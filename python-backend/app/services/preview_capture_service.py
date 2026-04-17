from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path

SLIDE_WIDTH = 1920
SLIDE_HEIGHT = 1080
POST_LOAD_WAIT_MS = 900
FONT_READY_TIMEOUT_MS = 4_000

CaptureHook = Callable[[], None | Awaitable[None]]
PageStartHook = Callable[[int, int, int], None | Awaitable[None]]


class PreviewCaptureDependencyError(RuntimeError):
    """Raised when the Playwright runtime is unavailable."""


class PreviewCaptureRenderError(RuntimeError):
    """Raised when preview rendering or screenshot capture fails."""


class PreviewCaptureService:
    _capture_lock = asyncio.Lock()

    def __init__(self, *, preview_base_url: str):
        self.preview_base_url = preview_base_url.rstrip("/")

    @property
    def capture_lock(self) -> asyncio.Lock:
        return self._capture_lock

    async def capture_slide_images(
        self,
        *,
        page_numbers: Sequence[int],
        capture_dir: Path,
        before_capture: CaptureHook | None = None,
        file_name_resolver: Callable[[int], str] | None = None,
        on_page_start: PageStartHook | None = None,
    ) -> list[Path]:
        if not page_numbers:
            return []

        try:
            from playwright.async_api import Error as PlaywrightError
            from playwright.async_api import TimeoutError as PlaywrightTimeoutError
            from playwright.async_api import async_playwright
        except ModuleNotFoundError as exc:
            raise PreviewCaptureDependencyError(
                "Python 后端缺少 Playwright 依赖，请先安装并在环境中执行 `playwright install chromium`。"
            ) from exc

        capture_dir.mkdir(parents=True, exist_ok=True)
        captured_paths: list[Path] = []

        try:
            async with self.capture_lock:
                await _maybe_await(before_capture)

                async with async_playwright() as playwright:
                    browser = await playwright.chromium.launch()
                    context = await browser.new_context(
                        viewport={"width": SLIDE_WIDTH, "height": SLIDE_HEIGHT},
                        screen={"width": SLIDE_WIDTH, "height": SLIDE_HEIGHT},
                        device_scale_factor=1,
                    )
                    page = await context.new_page()

                    try:
                        total = len(page_numbers)
                        for index, page_number in enumerate(page_numbers, start=1):
                            await _maybe_await(on_page_start, index, total, page_number)

                            slide_url = f"{self.preview_base_url}/slide/{page_number}"
                            await page.goto(slide_url, wait_until="load")
                            await page.wait_for_load_state("networkidle")
                            await page.wait_for_function(
                                "() => document.fonts ? document.fonts.status === 'loaded' : true",
                                timeout=FONT_READY_TIMEOUT_MS,
                            )
                            await page.wait_for_timeout(POST_LOAD_WAIT_MS)

                            file_name = (
                                file_name_resolver(page_number)
                                if file_name_resolver is not None
                                else f"page-{page_number:03d}.png"
                            )
                            screenshot_path = (capture_dir / file_name).resolve()
                            await page.screenshot(
                                path=str(screenshot_path),
                                animations="disabled",
                                type="png",
                            )
                            captured_paths.append(screenshot_path)
                    finally:
                        await context.close()
                        await browser.close()
        except PlaywrightTimeoutError as exc:
            raise PreviewCaptureRenderError("预览页面加载超时，请确认 preview server 已正常启动。") from exc
        except PlaywrightError as exc:
            error_message = str(exc)
            if "Executable doesn't exist" in error_message:
                raise PreviewCaptureDependencyError(
                    "Playwright Chromium 浏览器未安装，请在 python-backend 环境执行 `playwright install chromium`。"
                ) from exc
            raise PreviewCaptureRenderError(f"Playwright 截图失败：{error_message}") from exc

        return captured_paths


async def _maybe_await(callback: Callable[..., object] | None, *args: object) -> None:
    if callback is None:
        return

    result = callback(*args)
    if inspect.isawaitable(result):
        await result
