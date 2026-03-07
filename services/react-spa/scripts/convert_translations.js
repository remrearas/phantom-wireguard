#!/usr/bin/env node
/**
 * YAML to JSON translation converter
 *
 * Usage:  node scripts/convert_translations.js
 * Input:  ./translations.yaml
 * Output: ./src/shared/translations/translations.json
 */

import fs from 'fs';
import path from 'path';
import yaml from 'js-yaml';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const PROJECT_ROOT = path.resolve(__dirname, '..');
const INPUT_FILE = path.join(PROJECT_ROOT, 'translations.yaml');
const OUTPUT_FILE = path.join(PROJECT_ROOT, 'src', 'shared', 'translations', 'translations.json');

function convertYamlToJson() {
  if (!fs.existsSync(INPUT_FILE)) {
    console.error(`ERROR: Input file not found: ${INPUT_FILE}`);
    process.exit(1);
  }

  const yamlContent = fs.readFileSync(INPUT_FILE, 'utf8');
  const jsonData = yaml.load(yamlContent);

  if (typeof jsonData !== 'object' || jsonData === null) {
    console.error('[ERROR] Invalid YAML structure');
    process.exit(1);
  }

  const jsonContent = JSON.stringify(jsonData, null, 2);

  const outputDir = path.dirname(OUTPUT_FILE);
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  fs.writeFileSync(OUTPUT_FILE, jsonContent, 'utf8');

  const languages = Object.keys(jsonData).filter((k) => k !== '_default').length;
  console.log(`[OK] ${languages} languages → ${path.relative(PROJECT_ROOT, OUTPUT_FILE)}`);
}

convertYamlToJson();
