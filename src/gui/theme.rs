//! Thème inspiré de Fluent, le langage visuel de Windows 11.

use std::path::PathBuf;
use std::sync::Arc;

use eframe::egui;
use egui::epaint::Shadow;
use egui::{
    Color32, Context, CornerRadius, FontData, FontDefinitions, FontFamily, FontId, Stroke, Style,
    TextStyle, Theme, ThemePreference, Ui, Visuals, vec2,
};

const SEMIBOLD: &str = "semibold";
const ICONS: &str = "icons";

/// Glyphes de la police Segoe Fluent Icons.
pub mod icon {
    pub const ADD: char = '\u{E710}';
    pub const IMPORT: char = '\u{E8B5}';
    pub const EXPORT: char = '\u{EDE1}';
    pub const KEY: char = '\u{E8D7}';
    pub const CONNECT: char = '\u{E703}';
    pub const LOCK: char = '\u{E72E}';
    pub const SHOW: char = '\u{E7B3}';
    pub const HIDE: char = '\u{ED1A}';
    pub const COPY: char = '\u{E8C8}';
    pub const EDIT: char = '\u{E70F}';
    pub const DELETE: char = '\u{E74D}';
    pub const SUCCESS: char = '\u{E930}';
    pub const ERROR: char = '\u{EA39}';
}

#[derive(Clone, Copy)]
pub struct Palette {
    pub background: Color32,
    pub card: Color32,
    pub control: Color32,
    pub stroke: Color32,
    pub control_stroke: Color32,
    pub text: Color32,
    pub secondary: Color32,
    pub accent: Color32,
    pub on_accent: Color32,
    pub hover: Color32,
    pub pressed: Color32,
    pub success: Color32,
    pub success_background: Color32,
    pub danger: Color32,
    pub danger_background: Color32,
    pub warning: Color32,
}

const LIGHT: Palette = Palette {
    background: Color32::from_rgb(0xF3, 0xF3, 0xF3),
    card: Color32::from_rgb(0xFB, 0xFB, 0xFB),
    control: Color32::from_rgb(0xFF, 0xFF, 0xFF),
    stroke: Color32::from_rgb(0xE0, 0xE0, 0xE0),
    control_stroke: Color32::from_rgb(0x8A, 0x8A, 0x8A),
    text: Color32::from_rgb(0x1B, 0x1B, 0x1B),
    secondary: Color32::from_rgb(0x5D, 0x5D, 0x5D),
    accent: Color32::from_rgb(0x00, 0x5F, 0xB8),
    on_accent: Color32::WHITE,
    hover: Color32::from_rgb(0xE9, 0xE9, 0xE9),
    pressed: Color32::from_rgb(0xE0, 0xE0, 0xE0),
    success: Color32::from_rgb(0x0F, 0x7B, 0x0F),
    success_background: Color32::from_rgb(0xDF, 0xF6, 0xDD),
    danger: Color32::from_rgb(0xC4, 0x2B, 0x1C),
    danger_background: Color32::from_rgb(0xFD, 0xE7, 0xE9),
    warning: Color32::from_rgb(0x9D, 0x5D, 0x00),
};

const DARK: Palette = Palette {
    background: Color32::from_rgb(0x20, 0x20, 0x20),
    card: Color32::from_rgb(0x2B, 0x2B, 0x2B),
    control: Color32::from_rgb(0x33, 0x33, 0x33),
    stroke: Color32::from_rgb(0x40, 0x40, 0x40),
    control_stroke: Color32::from_rgb(0x85, 0x85, 0x85),
    text: Color32::from_rgb(0xFF, 0xFF, 0xFF),
    secondary: Color32::from_rgb(0xCF, 0xCF, 0xCF),
    accent: Color32::from_rgb(0x60, 0xCD, 0xFF),
    on_accent: Color32::BLACK,
    hover: Color32::from_rgb(0x38, 0x38, 0x38),
    pressed: Color32::from_rgb(0x2F, 0x2F, 0x2F),
    success: Color32::from_rgb(0x6C, 0xCB, 0x5F),
    success_background: Color32::from_rgb(0x39, 0x3D, 0x1B),
    danger: Color32::from_rgb(0xFF, 0x99, 0xA4),
    danger_background: Color32::from_rgb(0x44, 0x27, 0x26),
    warning: Color32::from_rgb(0xFC, 0xE1, 0x00),
};

pub fn palette(ui: &Ui) -> Palette {
    if ui.visuals().dark_mode { DARK } else { LIGHT }
}

/// Applique le thème, qui suit le mode clair ou sombre du système.
pub fn apply(ctx: &Context) {
    ctx.set_fonts(fonts());
    ctx.set_style_of(Theme::Light, style(Theme::Light));
    ctx.set_style_of(Theme::Dark, style(Theme::Dark));
    ctx.set_theme(ThemePreference::System);
}

/// La police des icônes n'existe que sous Windows : ailleurs, les boutons restent sans icône.
pub fn icon_font(ui: &Ui, size: f32) -> Option<FontId> {
    let family = FontFamily::Name(ICONS.into());
    ui.fonts(|fonts| fonts.families().contains(&family))
        .then(|| FontId::new(size, family))
}

// Les polices système ne sont pas redistribuables : on les lit sur place, sinon egui garde les siennes.
fn fonts() -> FontDefinitions {
    let mut fonts = FontDefinitions::default();
    let mut load = |name: &str, file: &str| {
        let bytes = std::fs::read(system_font(file)?).ok()?;
        fonts
            .font_data
            .insert(name.to_owned(), Arc::new(FontData::from_owned(bytes)));
        Some(())
    };
    let regular = load("segoe", "segoeui.ttf").is_some();
    let semibold = load(SEMIBOLD, "seguisb.ttf").is_some();
    let icons = load(ICONS, "SegoeIcons.ttf").is_some();

    let mut heading = fonts.families[&FontFamily::Proportional].clone();
    if semibold {
        heading.insert(0, SEMIBOLD.to_owned());
    }
    fonts
        .families
        .insert(FontFamily::Name(SEMIBOLD.into()), heading);
    if regular {
        fonts
            .families
            .get_mut(&FontFamily::Proportional)
            .expect("famille par défaut d'egui")
            .insert(0, "segoe".to_owned());
    }
    if icons {
        fonts
            .families
            .insert(FontFamily::Name(ICONS.into()), vec![ICONS.to_owned()]);
    }
    fonts
}

fn system_font(file: &str) -> Option<PathBuf> {
    let root = std::env::var_os("SystemRoot")?;
    Some(PathBuf::from(root).join("Fonts").join(file))
}

fn style(theme: Theme) -> Style {
    let (palette, mut visuals) = match theme {
        Theme::Light => (LIGHT, Visuals::light()),
        Theme::Dark => (DARK, Visuals::dark()),
    };
    let control_radius = CornerRadius::same(4);
    let card_radius = CornerRadius::same(8);

    visuals.panel_fill = palette.background;
    visuals.window_fill = palette.card;
    visuals.window_stroke = Stroke::new(1.0_f32, palette.stroke);
    visuals.window_corner_radius = card_radius;
    visuals.window_shadow = Shadow {
        offset: [0, 8],
        blur: 24,
        spread: 0,
        color: Color32::from_black_alpha(48),
    };
    visuals.popup_shadow = visuals.window_shadow;
    visuals.menu_corner_radius = card_radius;
    visuals.extreme_bg_color = palette.control;
    visuals.faint_bg_color = palette.card;
    visuals.hyperlink_color = palette.accent;
    visuals.error_fg_color = palette.danger;
    visuals.warn_fg_color = palette.warning;
    visuals.selection.bg_fill = palette.accent.gamma_multiply(0.35);
    visuals.selection.stroke = Stroke::new(1.5_f32, palette.accent);

    let widgets = &mut visuals.widgets;
    widgets.noninteractive.bg_stroke = Stroke::new(1.0_f32, palette.stroke);
    widgets.noninteractive.fg_stroke = Stroke::new(1.0_f32, palette.text);
    widgets.noninteractive.corner_radius = control_radius;
    for (state, fill) in [
        (&mut widgets.inactive, palette.control),
        (&mut widgets.hovered, palette.hover),
        (&mut widgets.active, palette.pressed),
        (&mut widgets.open, palette.hover),
    ] {
        state.bg_fill = fill;
        state.weak_bg_fill = fill;
        state.bg_stroke = Stroke::new(1.0_f32, palette.control_stroke);
        state.fg_stroke = Stroke::new(1.0_f32, palette.text);
        state.corner_radius = control_radius;
        state.expansion = 0.0;
    }

    let mut style = Style {
        visuals,
        ..Style::default()
    };
    style.text_styles = [
        (TextStyle::Small, FontId::proportional(12.0)),
        (TextStyle::Body, FontId::proportional(14.0)),
        (TextStyle::Button, FontId::proportional(14.0)),
        (TextStyle::Monospace, FontId::monospace(14.0)),
        (
            TextStyle::Heading,
            FontId::new(20.0, FontFamily::Name(SEMIBOLD.into())),
        ),
    ]
    .into();
    style.spacing.item_spacing = vec2(8.0, 8.0);
    style.spacing.button_padding = vec2(12.0, 6.0);
    style.spacing.interact_size.y = 32.0;
    style.spacing.window_margin = egui::Margin::same(24);
    style.spacing.menu_margin = egui::Margin::same(24);
    style
}

#[cfg(test)]
mod tests {
    use super::*;

    fn luminance(color: Color32) -> f32 {
        let channel = |value: u8| {
            let value = f32::from(value) / 255.0;
            if value <= 0.03928 {
                value / 12.92
            } else {
                ((value + 0.055) / 1.055).powf(2.4)
            }
        };
        0.2126 * channel(color.r()) + 0.7152 * channel(color.g()) + 0.0722 * channel(color.b())
    }

    fn contrast(a: Color32, b: Color32) -> f32 {
        let (a, b) = (luminance(a), luminance(b));
        (a.max(b) + 0.05) / (a.min(b) + 0.05)
    }

    #[test]
    fn control_borders_reach_the_wcag_contrast() {
        for palette in [LIGHT, DARK] {
            for fill in [palette.background, palette.card, palette.control] {
                assert!(contrast(palette.control_stroke, fill) >= 3.0);
            }
        }
    }
}
