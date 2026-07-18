"""Créer des documents de démonstration localement en français pour l'interface utilisateur."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docx import Document
from pptx import Presentation


SAMPLE_DIR = Path(__file__).resolve().parents[1] / "sample_docs"


def _clear_existing_samples() -> None:
    """Supprimer les anciens documents de démonstration dans le dossier sample_docs."""

    if not SAMPLE_DIR.exists():
        return
    for path in SAMPLE_DIR.iterdir():
        if path.is_file() and path.suffix.lower() in {".docx", ".pptx", ".pdf"}:
            path.unlink()


def create_radar_docx(path: Path) -> None:
    """Créer un rapport français sur un projet radar FPGA."""

    document = Document()
    document.core_properties.title = "Étude de faisabilité radar FPGA"
    document.core_properties.author = "Assistant de connaissances R&D"
    document.add_heading("Étude de faisabilité radar FPGA", level=1)
    document.add_paragraph(
        "Le projet radar a évalué une chaîne de traitement embarquée pour la détection à courte portée. "
        "L'équipe a mis en œuvre la compression d'impulsions, le rejet du clutter et le scoring des cibles sur un prototype FPGA."
    )
    document.add_heading("Architecture technique", level=2)
    document.add_paragraph(
        "L'architecture utilisait un FPGA Xilinx, un traitement du signal en virgule fixe et un processeur de contrôle léger. "
        "La latence est restée inférieure à 18 millisecondes lors des tests en banc, ce qui convient aux contraintes avioniques."
    )
    document.add_heading("Leçons apprises", level=2)
    document.add_paragraph(
        "Le principal risque concernait la bande passante mémoire pendant les fortes fréquences de répétition d'impulsions. "
        "Les travaux futurs compareront l'accélération FPGA à un traitement CPU uniquement pour les modes radar basse consommation."
    )
    document.save(path)


def create_sensor_docx(path: Path) -> None:
    """Créer une note française sur la fusion de capteurs inertiels et GNSS."""

    document = Document()
    document.core_properties.title = "Notes de fusion capteurs inertiels et GNSS"
    document.core_properties.author = "Assistant de connaissances R&D"
    document.add_heading("Notes de fusion capteurs inertiels et GNSS", level=1)
    document.add_paragraph(
        "Cette étude a comparé plusieurs stratégies de filtrage de Kalman pour combiner les mesures IMU, GNSS et altitude barométrique. "
        "Le meilleur résultat a utilisé un réglage adaptatif de covariance pendant la dégradation du GNSS."
    )
    document.add_heading("Résultats opérationnels", level=2)
    document.add_paragraph(
        "La solution de navigation est restée stable pendant de courtes coupures GNSS lorsque le biais IMU était recalibré avant le décollage. "
        "Les longues coupures nécessitent encore un appui par cartographie ou odométrie visuelle."
    )
    document.add_heading("Suivi recommandé", level=2)
    document.add_paragraph(
        "Le prochain prototype doit intégrer l'odométrie par vision par ordinateur et la comparer à la localisation par lidar."
    )
    document.save(path)


def create_uav_pptx(path: Path) -> None:
    """Créer une présentation française sur la navigation UAV."""

    presentation = Presentation()
    presentation.core_properties.title = "Feuille de route navigation UAV"
    presentation.core_properties.author = "Assistant de connaissances R&D"

    title_slide = presentation.slides.add_slide(presentation.slide_layouts[0])
    title_slide.shapes.title.text = "Feuille de route navigation UAV"
    title_slide.placeholders[1].text = "Priorités de navigation autonome pour la revue R&D"

    slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    slide.shapes.title.text = "Pile de navigation"
    slide.placeholders[1].text = (
        "La pile de navigation UAV combine GNSS, IMU, vision par ordinateur et fusion de capteurs. "
        "La feuille de route privilégie un fonctionnement robuste dans des environnements GNSS dégradés."
    )

    slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    slide.shapes.title.text = "Risques ouverts"
    slide.placeholders[1].text = (
        "Les risques ouverts incluent la dérive de l'odométrie visuelle, les limites de calcul embarqué et l'effort de validation pour les cas de sécurité avionique."
    )

    presentation.save(path)


def main() -> None:
    """Générer les documents de démonstration dans sample_docs."""

    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    _clear_existing_samples()
    create_radar_docx(SAMPLE_DIR / "etude_radar_fpga.docx")
    create_sensor_docx(SAMPLE_DIR / "fusion_capteurs_gnss.docx")
    create_uav_pptx(SAMPLE_DIR / "feuille_route_navigation_uav.pptx")
    print(f"Documents de démonstration écrits dans {SAMPLE_DIR}")


if __name__ == "__main__":
    main()
