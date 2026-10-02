import { useState } from "react";

function detectWebGL(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
  } catch {
    return false;
  }
}

/** Whether 3D can render here; checked once per component mount. */
export function useWebGL(): boolean {
  const [supported] = useState(detectWebGL);
  return supported;
}
