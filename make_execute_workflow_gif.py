from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent
HTML_FILE = ROOT / "index.html"
OUT_GIF = ROOT / "execute-workflow.gif"
TMP_DIR = ROOT / ".gif_frames"


def capture_frames() -> list[Path]:
    TMP_DIR.mkdir(exist_ok=True)
    for old in TMP_DIR.glob("frame-*.png"):
        old.unlink()

    frames: list[Path] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Render at higher pixel density for cleaner text/edges in GIF frames.
        page = browser.new_page(viewport={"width": 1360, "height": 980, "device_scale_factor": 2})
        page.goto(HTML_FILE.as_uri(), wait_until="networkidle")
        page.locator("#workflow").scroll_into_view_if_needed()
        page.wait_for_timeout(500)

        clip_target = page.locator(".wf-wrap")
        box = clip_target.bounding_box()
        if not box:
            raise RuntimeError("Could not locate workflow section for capture.")

        page.click("#wf-exec-btn")
        total_frames = 52
        step_ms = 120
        for i in range(total_frames):
            frame_path = TMP_DIR / f"frame-{i:03d}.png"
            page.screenshot(
                path=str(frame_path),
                clip={
                    "x": box["x"],
                    "y": box["y"],
                    "width": box["width"],
                    "height": box["height"],
                },
            )
            frames.append(frame_path)
            page.wait_for_timeout(step_ms)

        browser.close()
    return frames


def build_gif(frame_paths: list[Path]) -> None:
    rgb_images = [Image.open(path).convert("RGB") for path in frame_paths]
    # Keep original frame resolution; avoid extra downscale blur.
    gif_frames = [
        img.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        for img in rgb_images
    ]
    gif_frames[0].save(
        OUT_GIF,
        save_all=True,
        append_images=gif_frames[1:],
        duration=110,
        loop=0,
        optimize=False,
        disposal=2,
    )


def main() -> None:
    frame_paths = capture_frames()
    build_gif(frame_paths)
    print(f"Created GIF: {OUT_GIF}")


if __name__ == "__main__":
    main()
