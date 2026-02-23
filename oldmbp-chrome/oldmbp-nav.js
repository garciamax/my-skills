#!/usr/bin/env node

import puppeteer from "puppeteer-core";

const args = process.argv.slice(2);
const newTab = args.includes("--new");
const reload = args.includes("--reload");
const url = args.find(a => !a.startsWith("--"));

if (!url) {
	console.log("Usage: oldmbp-nav.js <url> [--new] [--reload]");
	console.log("\nExamples:");
	console.log("  oldmbp-nav.js https://example.com          # Navigate current tab");
	console.log("  oldmbp-nav.js https://example.com --new    # Open in new tab");
	console.log("  oldmbp-nav.js https://example.com --reload # Navigate and force reload");
	process.exit(1);
}

const OLDMBP_IP = "192.168.2.4";

const b = await Promise.race([
	puppeteer.connect({
		browserURL: `http://${OLDMBP_IP}:9222`,
		defaultViewport: null,
	}),
	new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), 5000)),
]).catch((e) => {
	console.error("✗ Could not connect to browser:", e.message);
	console.error("  Run: oldmbp-browser.sh start");
	process.exit(1);
});

if (newTab) {
	const p = await b.newPage();
	await p.goto(url, { waitUntil: "domcontentloaded" });
	console.log("✓ Opened:", url);
} else {
	const p = (await b.pages()).at(-1);
	await p.goto(url, { waitUntil: "domcontentloaded" });
	if (reload) {
		await p.reload({ waitUntil: "domcontentloaded" });
	}
	console.log("✓ Navigated to:", url);
}

await b.disconnect();
