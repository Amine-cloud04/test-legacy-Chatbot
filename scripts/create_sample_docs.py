"""Create repeatable local demo documents for UI testing."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docx import Document
from pptx import Presentation


SAMPLE_DIR = Path(__file__).resolve().parents[1] / "sample_docs"


def create_radar_docx(path: Path) -> None:
    """Create a radar/FPGA project report."""

    document = Document()
    document.core_properties.title = "ARES Radar FPGA Feasibility Study"
    document.core_properties.author = "R&D Knowledge Assistant Demo"
    document.add_heading("ARES Radar FPGA Feasibility Study", level=1)
    document.add_paragraph(
        "The ARES project evaluated an embedded radar processing chain for short-range detection. "
        "The team implemented pulse compression, clutter rejection, and target scoring on an FPGA prototype."
    )
    document.add_heading("Technical Architecture", level=2)
    document.add_paragraph(
        "The architecture used a Xilinx FPGA, fixed-point signal processing, and a lightweight control processor. "
        "Latency stayed below 18 milliseconds during bench tests, which made the approach suitable for avionics constraints."
    )
    document.add_heading("Lessons Learned", level=2)
    document.add_paragraph(
        "The main risk was memory bandwidth during high pulse repetition rates. "
        "Future work should compare FPGA acceleration with CPU-only processing for low-power radar modes."
    )
    document.save(path)


def create_sensor_docx(path: Path) -> None:
    """Create an inertial/GNSS sensor fusion note."""

    document = Document()
    document.core_properties.title = "Inertial GNSS Sensor Fusion Notes"
    document.core_properties.author = "R&D Knowledge Assistant Demo"
    document.add_heading("Inertial GNSS Sensor Fusion Notes", level=1)
    document.add_paragraph(
        "This study compared Kalman filtering strategies for combining IMU, GNSS, and barometric altitude measurements. "
        "The best result used adaptive covariance tuning during GNSS degradation."
    )
    document.add_heading("Operational Findings", level=2)
    document.add_paragraph(
        "The navigation solution remained stable during short GNSS outages when the IMU bias was recalibrated before takeoff. "
        "Long outages still required map matching or visual odometry support."
    )
    document.add_heading("Recommended Follow Up", level=2)
    document.add_paragraph(
        "The next prototype should integrate computer vision odometry and compare it with lidar-based localisation."
    )
    document.save(path)


def create_uav_pptx(path: Path) -> None:
    """Create a UAV navigation presentation."""

    presentation = Presentation()
    presentation.core_properties.title = "UAV Navigation Roadmap"
    presentation.core_properties.author = "R&D Knowledge Assistant Demo"

    title_slide = presentation.slides.add_slide(presentation.slide_layouts[0])
    title_slide.shapes.title.text = "UAV Navigation Roadmap"
    title_slide.placeholders[1].text = "Autonomous navigation priorities for R&D review"

    slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    slide.shapes.title.text = "Navigation Stack"
    slide.placeholders[1].text = (
        "The UAV navigation stack combines GNSS, IMU, computer vision, and sensor fusion. "
        "The roadmap prioritises robust operation in degraded GNSS environments."
    )

    slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    slide.shapes.title.text = "Open Risks"
    slide.placeholders[1].text = (
        "Open risks include visual odometry drift, embedded compute limits, and validation effort for avionics safety cases."
    )

    presentation.save(path)


def main() -> None:
    """Generate sample documents in sample_docs."""

    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    create_radar_docx(SAMPLE_DIR / "ares_radar_fpga_study.docx")
    create_sensor_docx(SAMPLE_DIR / "inertial_gnss_sensor_fusion.docx")
    create_uav_pptx(SAMPLE_DIR / "uav_navigation_roadmap.pptx")
    print(f"Sample documents written to {SAMPLE_DIR}")


if __name__ == "__main__":
    main()
