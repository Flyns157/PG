//! Formulaire au clavier.

use ratatui::Frame;
use ratatui::crossterm::event::{KeyCode, KeyEvent};
use ratatui::layout::{Constraint, Layout, Position, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Clear, Paragraph, Wrap};
use zeroize::Zeroizing;

pub struct Field {
    label: &'static str,
    value: Zeroizing<String>,
    cursor: usize,
    secret: bool,
    revealed: bool,
}

impl Field {
    pub fn text(label: &'static str) -> Self {
        Self {
            label,
            value: Zeroizing::default(),
            cursor: 0,
            secret: false,
            revealed: false,
        }
    }

    pub fn secret(label: &'static str) -> Self {
        Self {
            secret: true,
            ..Self::text(label)
        }
    }

    pub fn with_value(mut self, value: &str) -> Self {
        self.set(value);
        self
    }

    pub fn value(&self) -> &str {
        &self.value
    }

    pub fn set(&mut self, value: &str) {
        self.value = Zeroizing::new(value.to_owned());
        self.cursor = value.chars().count();
    }

    pub fn reveal(&mut self) {
        self.revealed = true;
    }

    fn byte_index(&self, cursor: usize) -> usize {
        self.value
            .char_indices()
            .nth(cursor)
            .map_or(self.value.len(), |(index, _)| index)
    }

    fn handle_key(&mut self, code: KeyCode) {
        let length = self.value.chars().count();
        match code {
            KeyCode::Char(character) => {
                let index = self.byte_index(self.cursor);
                self.value.insert(index, character);
                self.cursor += 1;
            }
            KeyCode::Backspace if self.cursor > 0 => {
                self.cursor -= 1;
                let index = self.byte_index(self.cursor);
                self.value.remove(index);
            }
            KeyCode::Delete if self.cursor < length => {
                let index = self.byte_index(self.cursor);
                self.value.remove(index);
            }
            KeyCode::Left => self.cursor = self.cursor.saturating_sub(1),
            KeyCode::Right => self.cursor = (self.cursor + 1).min(length),
            KeyCode::Home => self.cursor = 0,
            KeyCode::End => self.cursor = length,
            _ => {}
        }
    }

    fn display(&self) -> String {
        if self.secret && !self.revealed {
            "•".repeat(self.value.chars().count())
        } else {
            self.value.to_string()
        }
    }
}

pub struct Form {
    title: String,
    hint: &'static str,
    pub fields: Vec<Field>,
    focus: usize,
}

impl Form {
    pub fn new(title: impl Into<String>, hint: &'static str, fields: Vec<Field>) -> Self {
        Self {
            title: title.into(),
            hint,
            fields,
            focus: 0,
        }
    }

    pub fn value(&self, index: usize) -> &str {
        self.fields[index].value()
    }

    pub fn toggle_reveal(&mut self) {
        let field = &mut self.fields[self.focus];
        field.revealed = !field.revealed;
    }

    pub fn handle_key(&mut self, key: KeyEvent) {
        match key.code {
            KeyCode::Tab | KeyCode::Down => self.focus = (self.focus + 1) % self.fields.len(),
            KeyCode::BackTab | KeyCode::Up => {
                self.focus = (self.focus + self.fields.len() - 1) % self.fields.len()
            }
            code => self.fields[self.focus].handle_key(code),
        }
    }

    pub fn render(&self, frame: &mut Frame, status: Option<&Line<'_>>) {
        // Le statut et sa ligne de séparation n'occupent de place que s'il y a un message.
        let height = self.fields.len() as u16 + if status.is_some() { 4 } else { 2 };
        let [main_area, hint_area] =
            Layout::vertical([Constraint::Fill(1), Constraint::Length(2)]).areas(frame.area());
        let area = centered(main_area, 76, height);
        frame.render_widget(Clear, area);
        let block = Block::bordered().title(format!(" {} ", self.title));
        let inner = block.inner(area);
        frame.render_widget(block, area);

        let [fields_area, _, status_area] = Layout::vertical([
            Constraint::Length(self.fields.len() as u16),
            Constraint::Length(1),
            Constraint::Length(1),
        ])
        .areas(inner);
        let label_width = self
            .fields
            .iter()
            .map(|field| field.label.chars().count())
            .max()
            .unwrap_or(0) as u16
            + 2;

        for (index, field) in self.fields.iter().enumerate() {
            let focused = index == self.focus;
            let row = Rect {
                y: fields_area.y + index as u16,
                height: 1,
                ..fields_area
            };
            let label_style = if focused {
                Style::new().add_modifier(Modifier::BOLD)
            } else {
                Style::new().fg(Color::Gray)
            };
            let label = Span::styled(
                format!("{:<width$}", field.label, width = label_width as usize),
                label_style,
            );
            let available = row.width.saturating_sub(label_width + 1) as usize;
            // Fait défiler le champ pour garder le curseur visible.
            let offset = field.cursor.saturating_sub(available);
            let shown: String = field
                .display()
                .chars()
                .skip(offset)
                .take(available)
                .collect();
            frame.render_widget(
                Paragraph::new(Line::from(vec![label, Span::raw(shown)])),
                row,
            );
            if focused {
                let x = row.x + label_width + (field.cursor - offset) as u16;
                frame.set_cursor_position(Position::new(x, row.y));
            }
        }
        frame.render_widget(
            Paragraph::new(self.hint)
                .wrap(Wrap { trim: true })
                .style(Style::new().fg(Color::DarkGray)),
            hint_area,
        );
        if let Some(status) = status {
            frame.render_widget(Paragraph::new(status.clone()), status_area);
        }
    }
}

fn centered(area: Rect, width: u16, height: u16) -> Rect {
    let width = width.min(area.width);
    let height = height.min(area.height);
    Rect {
        x: area.x + (area.width - width) / 2,
        y: area.y + (area.height - height) / 2,
        width,
        height,
    }
}
