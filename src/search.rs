//! Recherche approchée dans le site, l'identifiant et les notes.

use fuzzy_matcher::FuzzyMatcher;
use fuzzy_matcher::skim::SkimMatcherV2;

use crate::entry::Entry;

/// Retourne les indices des entrées retenues : par pertinence, ou par site si `query` est vide.
pub fn filter(entries: &[Entry], query: &str) -> Vec<usize> {
    let query = query.trim();
    if query.is_empty() {
        let mut indices: Vec<usize> = (0..entries.len()).collect();
        indices.sort_by_cached_key(|&index| entries[index].fields.url.to_lowercase());
        return indices;
    }
    let matcher = SkimMatcherV2::default();
    let mut scored: Vec<(i64, usize)> = entries
        .iter()
        .enumerate()
        .filter_map(|(index, entry)| {
            let fields = &entry.fields;
            [&fields.url, &fields.username, &fields.notes]
                .into_iter()
                .filter_map(|text| matcher.fuzzy_match(text, query))
                .max()
                .map(|score| (score, index))
        })
        .collect();
    scored.sort_by(|a, b| b.0.cmp(&a.0).then(a.1.cmp(&b.1)));
    scored.into_iter().map(|(_, index)| index).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::entry::EntryFields;
    use chrono::Utc;

    fn entry(url: &str, username: &str) -> Entry {
        let fields = EntryFields::new(url, username, "p");
        Entry {
            id: url.into(),
            fields,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        }
    }

    #[test]
    fn empty_query_lists_everything_by_site() {
        let entries = [entry("zeta", "a"), entry("Alpha", "b")];
        assert_eq!(filter(&entries, "  "), vec![1, 0]);
    }

    #[test]
    fn query_matches_approximately_and_excludes_the_rest() {
        let entries = [
            entry("https://github.com", "moi"),
            entry("https://impots.gouv.fr", "toi"),
        ];
        assert_eq!(filter(&entries, "gthb"), vec![0]);
        assert_eq!(filter(&entries, "toi"), vec![1]);
        assert!(filter(&entries, "zzzzzz").is_empty());
    }
}
