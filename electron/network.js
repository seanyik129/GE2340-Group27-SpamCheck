"use strict";

const canvas = document.getElementById("network");
const context = canvas.getContext("2d");
const nodes = [
  [.53, .11], [.73, .08], [.91, .09], [.99, .17], [.63, .20],
  [.80, .19], [.92, .26], [.46, .29], [.68, .33], [.84, .35],
  [.98, .39], [.57, .43], [.75, .46], [.91, .52], [.62, .55],
  [.77, .60], [.99, .62], [.48, .65], [.67, .71], [.84, .73],
  [.96, .79], [.52, .82], [.76, .87], [.65, .94], [.92, .95],
  [.35, .19], [.37, .51], [.30, .79], [.58, .02], [.99, .01]
];

function drawNetwork() {
  if (!context) return;
  const { width, height } = canvas.getBoundingClientRect();
  const scale = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.round(width * scale);
  canvas.height = Math.round(height * scale);
  context.setTransform(scale, 0, 0, scale, 0, 0);

  const edge = context.createLinearGradient(width * .30, height, width, 0);
  edge.addColorStop(0, "rgba(94, 170, 255, 0.04)");
  edge.addColorStop(.55, "rgba(110, 177, 255, 0.24)");
  edge.addColorStop(1, "rgba(179, 121, 255, 0.39)");
  context.strokeStyle = edge;
  context.lineWidth = 1;
  context.beginPath();

  for (let first = 0; first < nodes.length; first++) {
    const [x, y] = nodes[first];
    for (let second = first + 1; second < nodes.length; second++) {
      const [nextX, nextY] = nodes[second];
      if (Math.hypot(x - nextX, (y - nextY) * 1.15) <= .23) {
        context.moveTo(x * width, y * height);
        context.lineTo(nextX * width, nextY * height);
      }
    }
  }
  context.stroke();

  for (const [index, [x, y]] of nodes.entries()) {
    const bright = x > .62 || index % 3 === 0;
    const color = y < .36 ? "#b39aff" : "#78c4ff";
    context.shadowBlur = bright ? 11 : 4;
    context.shadowColor = color;
    context.fillStyle = color;
    context.globalAlpha = bright ? .78 : .32;
    context.beginPath();
    context.arc(x * width, y * height, bright ? 2.5 : 1.5, 0, Math.PI * 2);
    context.fill();
  }
}

drawNetwork();
window.addEventListener("resize", drawNetwork);
