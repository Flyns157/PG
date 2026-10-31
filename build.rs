//! Intègre l'icône de l'application à l'exécutable Windows.

use std::path::Path;
use std::{env, fs};

const ICON: &str = "assets/icon.png";

fn main() {
    println!("cargo:rerun-if-changed={ICON}");
    if env::var("CARGO_CFG_TARGET_OS").as_deref() != Ok("windows") {
        return;
    }
    let png = fs::read(ICON).expect("icône de l'application illisible");
    let ico = Path::new(&env::var("OUT_DIR").unwrap()).join("icon.ico");
    fs::write(&ico, ico_from_png(&png)).expect("écriture de l'icône impossible");
    winresource::WindowsResource::new()
        .set_icon(ico.to_str().expect("chemin de compilation non UTF-8"))
        .compile()
        .expect("intégration de l'icône impossible");
}

/// Enveloppe un PNG dans un conteneur ICO à une image, seul format accepté par les ressources Windows.
fn ico_from_png(png: &[u8]) -> Vec<u8> {
    // Dans un PNG, la largeur et la hauteur occupent les octets 16 à 23 en gros-boutiste.
    let dimension =
        |offset: usize| match u32::from_be_bytes(png[offset..offset + 4].try_into().unwrap()) {
            256 => 0,
            size => u8::try_from(size).expect("une icône ne dépasse pas 256 pixels"),
        };
    const HEADER_LEN: u32 = 6 + 16;
    let mut ico = vec![
        0,
        0,
        1,
        0,
        1,
        0,
        dimension(16),
        dimension(20),
        0,
        0,
        1,
        0,
        32,
        0,
    ];
    ico.extend_from_slice(&(png.len() as u32).to_le_bytes());
    ico.extend_from_slice(&HEADER_LEN.to_le_bytes());
    ico.extend_from_slice(png);
    ico
}
