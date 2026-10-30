//! Interface en terminal.

mod app;
mod form;

use std::io;
use std::time::Duration;

use ratatui::crossterm::event::{self, Event, KeyEventKind};

use crate::store::Store;
use app::App;

const TICK: Duration = Duration::from_millis(250);

pub fn run(store: Store) -> io::Result<()> {
    let mut terminal = ratatui::init();
    let result = event_loop(&mut terminal, App::new(store));
    ratatui::restore();
    result
}

fn event_loop(terminal: &mut ratatui::DefaultTerminal, mut app: App) -> io::Result<()> {
    while !app.should_quit() {
        terminal.draw(|frame| app.render(frame))?;
        if event::poll(TICK)?
            && let Event::Key(key) = event::read()?
            && key.kind != KeyEventKind::Release
        {
            app.handle_key(key);
        }
        app.tick();
    }
    Ok(())
}
