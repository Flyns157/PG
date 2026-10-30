//! État commun aux interfaces : le coffre déverrouillé, la recherche et la sélection.

use crate::entry::Entry;
use crate::error::Result;
use crate::search;
use crate::store::{Session, Store};

pub struct Workspace {
    pub session: Session,
    entries: Vec<Entry>,
    query: String,
    visible: Vec<usize>,
    selected: usize,
}

impl Workspace {
    pub fn open(store: &Store, session: Session) -> Result<Self> {
        let mut workspace = Self {
            session,
            entries: Vec::new(),
            query: String::new(),
            visible: Vec::new(),
            selected: 0,
        };
        workspace.reload(store)?;
        Ok(workspace)
    }

    pub fn reload(&mut self, store: &Store) -> Result<()> {
        self.entries = store.list(&self.session)?;
        self.refilter();
        Ok(())
    }

    pub fn all_entries(&self) -> &[Entry] {
        &self.entries
    }

    pub fn query(&self) -> &str {
        &self.query
    }

    pub fn set_query(&mut self, query: &str) {
        self.query = query.to_owned();
        self.selected = 0;
        self.refilter();
    }

    fn refilter(&mut self) {
        self.visible = search::filter(&self.entries, &self.query);
        self.selected = self.selected.min(self.visible.len().saturating_sub(1));
    }

    pub fn visible(&self) -> impl ExactSizeIterator<Item = &Entry> {
        self.visible.iter().map(|&index| &self.entries[index])
    }

    pub fn selected_position(&self) -> usize {
        self.selected
    }

    pub fn select(&mut self, position: usize) {
        self.selected = position.min(self.visible.len().saturating_sub(1));
    }

    pub fn move_selection(&mut self, delta: isize) {
        self.select(self.selected.saturating_add_signed(delta));
    }

    pub fn selected(&self) -> Option<&Entry> {
        self.visible
            .get(self.selected)
            .map(|&index| &self.entries[index])
    }

    pub fn select_id(&mut self, id: &str) {
        if let Some(position) = self
            .visible
            .iter()
            .position(|&index| self.entries[index].id == id)
        {
            self.selected = position;
        }
    }
}
