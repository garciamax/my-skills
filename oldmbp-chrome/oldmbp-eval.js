#!/usr/bin/env node

import puppeteer from "puppeteer-core";

const code = process.argv.slice(2).join(" ");
if (!code) {
	console.log("Usage: oldmbp-eval.js 'code'");
	console.log("\nExamples:");
	console.log('  oldmbp-eval.js "document.title"');
	console.log('  oldmbp-eval.js "document.querySelectorAll(\'a\').length"');
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

const p = (await b.pages()).at(-1);

if (!p) {
	console.error("✗ No active tab found");
	process.exit(1);
}

const result = await p.evaluate((c) => {
	const AsyncFunction = (async () => {}).constructor;
	return new AsyncFunction(`return (${c})`)();
}, code);

if (Array.isArray(result)) {
	for (let i = 0; i < result.length; i++) {
		if (i > 0) console.log("");
		for (const [key, value] of Object.entries(result[i])) {
			console.log(`${key}: ${value}`);
		}
	}
} else if (typeof result === "object" && result !== null) {
	for (const [key, value] of Object.entries(result)) {
		console.log(`${key}: ${value}`);
	}
} else {
	console.log(result);
}

await b.disconnect();
