//! Serveur MCP local, désactivé par défaut (transport HTTP, réponses JSON).
//!
//! Il n'écoute que sur 127.0.0.1 et exige un jeton renouvelé à chaque activation. Les appels
//! sont exécutés par le fil de l'interface : un coffre verrouillé ne répond donc à aucun outil.
//! Un mot de passe ne sort jamais par ce serveur : il va seulement au presse-papiers.

use std::io::{ErrorKind, Read, Write};
use std::net::{SocketAddr, TcpListener, TcpStream};
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc::{self, Receiver, Sender};
use std::thread::{self, JoinHandle};
use std::time::{Duration, Instant};

use rand::Rng;
use serde_json::{Value, json};

use crate::clipboard::SecretClipboard;
use crate::search;
use crate::workspace::Workspace;

pub const PORT: u16 = 39517;

const PROTOCOL_VERSIONS: [&str; 2] = ["2025-06-18", "2025-03-26"];
const MAX_HEADERS: usize = 8 * 1024;
const MAX_BODY: usize = 64 * 1024;
const READ_DEADLINE: Duration = Duration::from_secs(5);
const READ_POLL: Duration = Duration::from_millis(200);
const ACCEPT_POLL: Duration = Duration::from_millis(50);
const CALL_TIMEOUT: Duration = Duration::from_secs(5);

/// Réveille l'interface pour qu'elle traite un appel en attente.
pub type Waker = Box<dyn Fn() + Send>;

enum ToolCall {
    Search(String),
    CopyPassword(String),
}

struct PendingCall {
    tool: ToolCall,
    reply: Sender<Result<String, String>>,
}

pub struct McpServer {
    url: String,
    token: String,
    stop: Arc<AtomicBool>,
    calls: Option<Receiver<PendingCall>>,
    thread: Option<JoinHandle<()>>,
}

impl McpServer {
    pub fn start(waker: Waker) -> std::io::Result<Self> {
        Self::start_on(PORT, waker)
    }

    pub(crate) fn start_on(port: u16, waker: Waker) -> std::io::Result<Self> {
        let listener = TcpListener::bind(SocketAddr::from(([127, 0, 0, 1], port)))?;
        listener.set_nonblocking(true)?;
        let port = listener.local_addr()?.port();
        let token = new_token();
        let stop = Arc::new(AtomicBool::new(false));
        let (sender, calls) = mpsc::channel();
        let connection = Connection {
            port,
            token: token.clone(),
            stop: Arc::clone(&stop),
            calls: sender,
            waker,
        };
        let thread = thread::spawn(move || connection.accept_loop(listener));
        Ok(Self {
            url: format!("http://127.0.0.1:{port}/mcp"),
            token,
            stop,
            calls: Some(calls),
            thread: Some(thread),
        })
    }

    pub fn url(&self) -> &str {
        &self.url
    }

    pub fn token(&self) -> &str {
        &self.token
    }

    /// Exécute les appels en attente et renvoie les messages à montrer à l'utilisateur.
    pub fn handle_pending(
        &self,
        workspace: Option<&Workspace>,
        mut copy: impl FnMut(&str) -> Result<(), String>,
    ) -> Vec<String> {
        let mut notices = Vec::new();
        let Some(calls) = &self.calls else {
            return notices;
        };
        while let Ok(call) = calls.try_recv() {
            let result = match workspace {
                None => Err("Le coffre est verrouillé : déverrouillez-le dans PG".to_owned()),
                Some(workspace) => run_tool(call.tool, workspace, &mut copy, &mut notices),
            };
            let _ = call.reply.send(result);
        }
        notices
    }
}

impl Drop for McpServer {
    fn drop(&mut self) {
        self.stop.store(true, Ordering::Relaxed);
        // Fermer la file libère aussitôt une connexion qui attend sa réponse.
        drop(self.calls.take());
        if let Some(thread) = self.thread.take() {
            let _ = thread.join();
        }
    }
}

/// Active ou désactive le serveur. L'activation copie le nouveau jeton.
pub fn toggle(
    server: &mut Option<McpServer>,
    clipboard: &mut SecretClipboard,
    waker: Waker,
) -> Result<String, String> {
    if server.take().is_some() {
        return Ok("Serveur MCP désactivé".to_owned());
    }
    let started = McpServer::start(waker)
        .map_err(|error| format!("Serveur MCP non démarré (port {PORT}) : {error}"))?;
    let message = copy_token(&started, clipboard);
    *server = Some(started);
    Ok(message)
}

pub fn copy_token(server: &McpServer, clipboard: &mut SecretClipboard) -> String {
    match clipboard.copy(server.token()) {
        Ok(()) => format!(
            "MCP actif sur {} · jeton copié (effacé dans 30 s)",
            server.url()
        ),
        Err(_) => format!(
            "MCP actif sur {} · jeton : {}",
            server.url(),
            server.token()
        ),
    }
}

fn run_tool(
    tool: ToolCall,
    workspace: &Workspace,
    copy: &mut impl FnMut(&str) -> Result<(), String>,
    notices: &mut Vec<String>,
) -> Result<String, String> {
    let entries = workspace.all_entries();
    match tool {
        ToolCall::Search(query) => {
            let found: Vec<Value> = search::filter(entries, &query)
                .into_iter()
                .map(|index| {
                    let entry = &entries[index];
                    json!({
                        "id": entry.id,
                        "url": entry.fields.url,
                        "username": entry.fields.username,
                        "notes": entry.fields.notes,
                    })
                })
                .collect();
            Ok(Value::Array(found).to_string())
        }
        ToolCall::CopyPassword(id) => {
            let entry = entries
                .iter()
                .find(|entry| entry.id == id)
                .ok_or("Entrée introuvable")?;
            copy(&entry.fields.password)
                .map_err(|error| format!("Presse-papiers indisponible : {error}"))?;
            notices.push(format!(
                "MCP : mot de passe de {} copié (effacé dans 30 s)",
                entry.fields.url
            ));
            Ok("Mot de passe copié dans le presse-papiers, effacé dans 30 s".to_owned())
        }
    }
}

fn new_token() -> String {
    let mut bytes = [0u8; 32];
    rand::rng().fill_bytes(&mut bytes);
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn same_token(given: &str, expected: &str) -> bool {
    given.len() == expected.len()
        && given
            .bytes()
            .zip(expected.bytes())
            .fold(0, |difference, (a, b)| difference | (a ^ b))
            == 0
}

struct Request {
    method: String,
    path: String,
    headers: Vec<(String, String)>,
    body: Vec<u8>,
}

impl Request {
    fn header(&self, name: &str) -> Option<&str> {
        self.headers
            .iter()
            .find(|(key, _)| key == name)
            .map(|(_, value)| value.as_str())
    }
}

enum ReadError {
    Closed,
    Malformed,
    TooLarge,
}

struct Connection {
    port: u16,
    token: String,
    stop: Arc<AtomicBool>,
    calls: Sender<PendingCall>,
    waker: Waker,
}

impl Connection {
    fn accept_loop(self, listener: TcpListener) {
        while !self.stop.load(Ordering::Relaxed) {
            match listener.accept() {
                Ok((stream, _)) => {
                    let _ = self.serve(stream);
                }
                Err(_) => thread::sleep(ACCEPT_POLL),
            }
        }
    }

    fn serve(&self, mut stream: TcpStream) -> std::io::Result<()> {
        stream.set_nonblocking(false)?;
        stream.set_read_timeout(Some(READ_POLL))?;
        stream.set_write_timeout(Some(READ_DEADLINE))?;
        let request = match self.read_request(&mut stream) {
            Ok(request) => request,
            Err(ReadError::Closed) => return Ok(()),
            Err(ReadError::Malformed) => return respond(&mut stream, "400 Bad Request", None),
            Err(ReadError::TooLarge) => return respond(&mut stream, "413 Too Large", None),
        };
        if !self.allowed_origin(&request) {
            return respond(&mut stream, "403 Forbidden", None);
        }
        if request.path != "/mcp" {
            return respond(&mut stream, "404 Not Found", None);
        }
        if request.method != "POST" {
            return respond(&mut stream, "405 Method Not Allowed", None);
        }
        let authorized = request
            .header("authorization")
            .and_then(|value| value.strip_prefix("Bearer "))
            .is_some_and(|given| same_token(given, &self.token));
        if !authorized {
            return respond(&mut stream, "401 Unauthorized", None);
        }
        match self.handle_message(&request.body) {
            Some(answer) => respond(&mut stream, "200 OK", Some(&answer)),
            None => respond(&mut stream, "202 Accepted", None),
        }
    }

    /// Bloque les pages web qui viseraient le serveur local (DNS rebinding compris).
    fn allowed_origin(&self, request: &Request) -> bool {
        let hosts = [
            format!("127.0.0.1:{}", self.port),
            format!("localhost:{}", self.port),
        ];
        let host_ok = request
            .header("host")
            .is_some_and(|host| hosts.iter().any(|allowed| allowed == host));
        let origin_ok = request.header("origin").is_none_or(|origin| {
            origin
                .strip_prefix("http://")
                .is_some_and(|host| hosts.iter().any(|allowed| allowed == host))
        });
        host_ok && origin_ok
    }

    fn read_request(&self, stream: &mut TcpStream) -> Result<Request, ReadError> {
        let deadline = Instant::now() + READ_DEADLINE;
        let mut buffer = Vec::new();
        let header_end = loop {
            if let Some(position) = buffer.windows(4).position(|window| window == b"\r\n\r\n") {
                break position;
            }
            if buffer.len() > MAX_HEADERS {
                return Err(ReadError::TooLarge);
            }
            self.read_more(stream, &mut buffer, deadline)?;
        };
        let head = std::str::from_utf8(&buffer[..header_end]).map_err(|_| ReadError::Malformed)?;
        let mut lines = head.split("\r\n");
        let mut request_line = lines.next().unwrap_or_default().split(' ');
        let (Some(method), Some(path)) = (request_line.next(), request_line.next()) else {
            return Err(ReadError::Malformed);
        };
        let headers: Vec<(String, String)> = lines
            .filter_map(|line| line.split_once(':'))
            .map(|(key, value)| (key.trim().to_ascii_lowercase(), value.trim().to_owned()))
            .collect();
        let mut request = Request {
            method: method.to_owned(),
            path: path.to_owned(),
            headers,
            body: Vec::new(),
        };
        let length = match request.header("content-length") {
            Some(value) => value.parse().map_err(|_| ReadError::Malformed)?,
            None => 0,
        };
        if length > MAX_BODY {
            return Err(ReadError::TooLarge);
        }
        let body_start = header_end + 4;
        while buffer.len() < body_start + length {
            self.read_more(stream, &mut buffer, deadline)?;
        }
        request.body = buffer[body_start..body_start + length].to_vec();
        Ok(request)
    }

    fn read_more(
        &self,
        stream: &mut TcpStream,
        buffer: &mut Vec<u8>,
        deadline: Instant,
    ) -> Result<(), ReadError> {
        let mut chunk = [0u8; 4096];
        loop {
            if self.stop.load(Ordering::Relaxed) || Instant::now() >= deadline {
                return Err(ReadError::Closed);
            }
            match stream.read(&mut chunk) {
                Ok(0) => return Err(ReadError::Closed),
                Ok(count) => {
                    buffer.extend_from_slice(&chunk[..count]);
                    return Ok(());
                }
                Err(error)
                    if matches!(
                        error.kind(),
                        ErrorKind::WouldBlock | ErrorKind::TimedOut | ErrorKind::Interrupted
                    ) => {}
                Err(_) => return Err(ReadError::Closed),
            }
        }
    }

    /// Renvoie `None` pour une notification, qui n'attend pas de réponse.
    fn handle_message(&self, body: &[u8]) -> Option<String> {
        let Ok(message) = serde_json::from_slice::<Value>(body) else {
            return Some(rpc_error(&Value::Null, -32700, "JSON invalide"));
        };
        let Some(method) = message.get("method").and_then(Value::as_str) else {
            // Un objet sans méthode est une réponse du client : rien à lui renvoyer.
            return (!message.is_object())
                .then(|| rpc_error(&Value::Null, -32600, "Requête invalide"));
        };
        let id = message.get("id")?;
        let params = message.get("params").unwrap_or(&Value::Null);
        let result = match method {
            "initialize" => Ok(initialize_result(params)),
            "ping" => Ok(json!({})),
            "tools/list" => Ok(json!({ "tools": tool_definitions() })),
            "tools/call" => self.call_tool(params),
            _ => Err((-32601, "Méthode inconnue".to_owned())),
        };
        Some(match result {
            Ok(result) => json!({ "jsonrpc": "2.0", "id": id, "result": result }).to_string(),
            Err((code, error)) => rpc_error(id, code, &error),
        })
    }

    fn call_tool(&self, params: &Value) -> Result<Value, (i64, String)> {
        let arguments = params.get("arguments").unwrap_or(&Value::Null);
        let text = |name: &str| arguments.get(name).and_then(Value::as_str);
        let tool = match params.get("name").and_then(Value::as_str) {
            Some("search_entries") => {
                ToolCall::Search(text("query").unwrap_or_default().to_owned())
            }
            Some("copy_password") => {
                let id = text("id").ok_or((-32602, "Argument « id » manquant".to_owned()))?;
                ToolCall::CopyPassword(id.to_owned())
            }
            _ => return Err((-32602, "Outil inconnu".to_owned())),
        };
        let (text, is_error) = match self.run_on_interface(tool) {
            Ok(text) => (text, false),
            Err(error) => (error, true),
        };
        Ok(json!({
            "content": [{ "type": "text", "text": text }],
            "isError": is_error,
        }))
    }

    fn run_on_interface(&self, tool: ToolCall) -> Result<String, String> {
        let (reply, answer) = mpsc::channel();
        self.calls
            .send(PendingCall { tool, reply })
            .map_err(|_| "Le serveur MCP s'arrête".to_owned())?;
        (self.waker)();
        answer
            .recv_timeout(CALL_TIMEOUT)
            .map_err(|_| "PG ne répond pas : sa fenêtre est peut-être réduite".to_owned())?
    }
}

fn initialize_result(params: &Value) -> Value {
    let requested = params.get("protocolVersion").and_then(Value::as_str);
    let version = PROTOCOL_VERSIONS
        .into_iter()
        .find(|version| Some(*version) == requested)
        .unwrap_or(PROTOCOL_VERSIONS[0]);
    json!({
        "protocolVersion": version,
        "capabilities": { "tools": {} },
        "serverInfo": { "name": "pg", "version": env!("CARGO_PKG_VERSION") },
        "instructions": "Coffre de mots de passe PG. Les mots de passe ne sont jamais renvoyés : \
                         copy_password les place dans le presse-papiers de l'utilisateur.",
    })
}

fn tool_definitions() -> Value {
    json!([
        {
            "name": "search_entries",
            "description": "Cherche dans le coffre et renvoie l'id, le site, l'identifiant et \
                            les notes des entrées, sans aucun mot de passe. Une recherche vide \
                            renvoie tout le coffre.",
            "inputSchema": {
                "type": "object",
                "properties": { "query": { "type": "string" } },
            },
            "annotations": { "readOnlyHint": true },
        },
        {
            "name": "copy_password",
            "description": "Copie le mot de passe d'une entrée dans le presse-papiers de \
                            l'utilisateur, effacé après 30 secondes. Le mot de passe n'est pas \
                            renvoyé.",
            "inputSchema": {
                "type": "object",
                "properties": { "id": { "type": "string" } },
                "required": ["id"],
            },
        },
    ])
}

fn rpc_error(id: &Value, code: i64, message: &str) -> String {
    json!({
        "jsonrpc": "2.0",
        "id": id,
        "error": { "code": code, "message": message },
    })
    .to_string()
}

fn respond(stream: &mut TcpStream, status: &str, body: Option<&str>) -> std::io::Result<()> {
    let body = body.unwrap_or_default();
    write!(
        stream,
        "HTTP/1.1 {status}\r\nContent-Type: application/json\r\nContent-Length: {}\r\n\
         Connection: close\r\n\r\n{body}",
        body.len()
    )?;
    stream.flush()
}

/// Envoie une requête JSON-RPC à un serveur de test et renvoie le statut et le corps.
#[cfg(test)]
pub(crate) fn post(url: &str, token: &str, body: &str) -> (u16, String) {
    let address = url.trim_start_matches("http://").trim_end_matches("/mcp");
    raw_request(
        address,
        &format!(
            "POST /mcp HTTP/1.1\r\nHost: {address}\r\nAuthorization: Bearer {token}\r\n\
             Content-Length: {}\r\n\r\n{body}",
            body.len()
        ),
    )
}

#[cfg(test)]
fn raw_request(address: &str, request: &str) -> (u16, String) {
    let mut stream = TcpStream::connect(address).unwrap();
    stream.write_all(request.as_bytes()).unwrap();
    let mut response = String::new();
    stream.read_to_string(&mut response).unwrap();
    let status = response[9..12].parse().unwrap();
    let (_, body) = response.split_once("\r\n\r\n").unwrap();
    (status, body.to_owned())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::entry::EntryFields;
    use crate::store::{FAST_KDF, Store};

    const SECRET: &str = "s3cret-ne-doit-pas-sortir";

    fn server() -> McpServer {
        McpServer::start_on(0, Box::new(|| {})).unwrap()
    }

    fn workspace() -> Workspace {
        let store = Store::open_in_memory().unwrap().with_kdf(FAST_KDF);
        let session = store.register("alice", "correct horse battery").unwrap();
        let mut fields = EntryFields::new("https://a.example", "moi", SECRET);
        fields.notes = "ma note".to_owned();
        store.add(&session, fields).unwrap();
        Workspace::open(&store, session).unwrap()
    }

    /// Lance un appel dans un fil pendant que le fil courant joue le rôle de l'interface.
    fn call(
        server: &McpServer,
        workspace: Option<&Workspace>,
        copied: &mut Vec<String>,
        body: &str,
    ) -> Value {
        let (url, token, body) = (server.url.clone(), server.token.clone(), body.to_owned());
        let client = thread::spawn(move || post(&url, &token, &body));
        while !client.is_finished() {
            server.handle_pending(workspace, |text| {
                copied.push(text.to_owned());
                Ok(())
            });
            thread::sleep(Duration::from_millis(5));
        }
        let (status, body) = client.join().unwrap();
        assert_eq!(status, 200, "{body}");
        serde_json::from_str(&body).unwrap()
    }

    fn tool_call(name: &str, arguments: Value) -> String {
        json!({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": { "name": name, "arguments": arguments },
        })
        .to_string()
    }

    fn address(server: &McpServer) -> String {
        server
            .url
            .trim_start_matches("http://")
            .trim_end_matches("/mcp")
            .to_owned()
    }

    #[test]
    fn initialize_negotiates_the_protocol_and_lists_tools() {
        let server = server();
        let mut copied = Vec::new();
        let answer = call(
            &server,
            None,
            &mut copied,
            r#"{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26"}}"#,
        );
        assert_eq!(answer["result"]["protocolVersion"], "2025-03-26");
        let answer = call(
            &server,
            None,
            &mut copied,
            r#"{"jsonrpc":"2.0","id":2,"method":"tools/list"}"#,
        );
        assert_eq!(answer["result"]["tools"].as_array().unwrap().len(), 2);
    }

    #[test]
    fn notification_gets_no_body() {
        let server = server();
        let (status, body) = post(
            &server.url,
            &server.token,
            r#"{"jsonrpc":"2.0","method":"notifications/initialized"}"#,
        );
        assert_eq!(status, 202);
        assert!(body.is_empty());
    }

    #[test]
    fn search_returns_entries_without_any_password() {
        let server = server();
        let workspace = workspace();
        let answer = call(
            &server,
            Some(&workspace),
            &mut Vec::new(),
            &tool_call("search_entries", json!({ "query": "" })),
        );
        let text = answer["result"]["content"][0]["text"].as_str().unwrap();
        assert!(text.contains("https://a.example"));
        assert!(text.contains("ma note"));
        assert!(!answer.to_string().contains(SECRET));
    }

    #[test]
    fn copy_password_uses_the_clipboard_and_never_the_response() {
        let server = server();
        let workspace = workspace();
        let id = workspace.all_entries()[0].id.clone();
        let mut copied = Vec::new();
        let answer = call(
            &server,
            Some(&workspace),
            &mut copied,
            &tool_call("copy_password", json!({ "id": id })),
        );
        assert_eq!(answer["result"]["isError"], false);
        assert_eq!(copied, [SECRET]);
        assert!(!answer.to_string().contains(SECRET));
    }

    #[test]
    fn locked_vault_answers_with_a_tool_error() {
        let server = server();
        let answer = call(
            &server,
            None,
            &mut Vec::new(),
            &tool_call("search_entries", json!({})),
        );
        assert_eq!(answer["result"]["isError"], true);
    }

    #[test]
    fn wrong_token_is_rejected() {
        let server = server();
        let (status, _) = post(&server.url, "mauvais", "{}");
        assert_eq!(status, 401);
    }

    #[test]
    fn web_origins_and_foreign_hosts_are_rejected() {
        let server = server();
        let address = address(&server);
        let token = &server.token;
        let origin = format!(
            "POST /mcp HTTP/1.1\r\nHost: {address}\r\nOrigin: https://evil.example\r\n\
             Authorization: Bearer {token}\r\nContent-Length: 0\r\n\r\n"
        );
        assert_eq!(raw_request(&address, &origin).0, 403);
        let host = format!(
            "POST /mcp HTTP/1.1\r\nHost: evil.example\r\n\
             Authorization: Bearer {token}\r\nContent-Length: 0\r\n\r\n"
        );
        assert_eq!(raw_request(&address, &host).0, 403);
    }

    #[test]
    fn oversized_body_and_other_methods_are_refused() {
        let server = server();
        let address = address(&server);
        let oversized = format!(
            "POST /mcp HTTP/1.1\r\nHost: {address}\r\nContent-Length: {}\r\n\r\n",
            MAX_BODY + 1
        );
        assert_eq!(raw_request(&address, &oversized).0, 413);
        let get = format!("GET /mcp HTTP/1.1\r\nHost: {address}\r\n\r\n");
        assert_eq!(raw_request(&address, &get).0, 405);
    }

    #[test]
    fn stopping_closes_the_port_even_with_a_waiting_call() {
        let server = server();
        let address = address(&server);
        let (url, token) = (server.url.clone(), server.token.clone());
        let client =
            thread::spawn(move || post(&url, &token, &tool_call("search_entries", json!({}))));
        thread::sleep(Duration::from_millis(100));
        let started = Instant::now();
        drop(server);
        assert!(started.elapsed() < CALL_TIMEOUT);
        client.join().unwrap();
        assert!(TcpStream::connect(address).is_err());
    }
}
