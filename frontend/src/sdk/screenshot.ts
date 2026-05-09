import { toPng } from "html-to-image";

export async function captureScreenshot(root: HTMLElement): Promise<string> {
  try {
    return await toPng(root, {
      cacheBust: true,
      backgroundColor: "#f7f5ef"
    });
  } catch {
    return "data:image/png;base64,";
  }
}

