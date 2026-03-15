#!/usr/bin/env node
/**
 * ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
 * ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
 * ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
 * ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
 * ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
 * ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
 * Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
 * 
 * TR: Phantom Documentation Kit Vendor Builder (build.js)
 * =======================================================
 * 
 * Bu script, Phantom Documentation Kit'in JS/CSS bağımlılıklarını yöneten kritik bir
 * bileşendir. Modern web uygulamalarında kullanılan JavaScript ve CSS kütüphanelerini 
 * optimize ederek, performanslı ve güvenilir bir deneyim sağlamak amaçlanmıştır.
 *
 * Önemli Notlar
 * --------------
 * Bu script'in sunduğu optimizasyon yetenekleri, projenizin özgün gereksinimlerine göre hassas 
 * bir şekilde ayarlanabilir. minifyJavaScript ve minifyCSS metodları, Terser ve PostCSS'in güçlü 
 * özelliklerini kullanarak kodunuzu optimize eder. Mevcut konfigürasyon, güvenli ve dengeli bir 
 * başlangıç noktası sağlar, ancak projenizin ihtiyaçlarına göre bu ayarları özelleştirebilirsiniz.
 * 
 * Örnek kullanım senaryoları:
 * 
 * dependencies.json yapılandırması:
 *   {
 *     "dependencies": [
 *       {
 *         "name": "Chart.js",
 *         "from": "node_modules/chart.js/dist/chart.umd.js",
 *         "to": "chart.min.js",
 *         "type": "js",
 *         "minify": true
 *       },
 *       {
 *         "name": "Font Awesome CSS",
 *         "from": "node_modules/@fortawesome/fontawesome-free/css/all.css",
 *         "to": "fontawesome.min.css",
 *         "type": "css",
 *         "minify": true
 *       }
 *     ]
 *   }
 *   - name: Kütüphane adı (loglama için)
 *   - from: Kaynak dosya yolu (node_modules içinde)
 *   - to: Hedef dosya adı (vendor/ dizininde)
 *   - type: Dosya tipi ("js" veya "css")
 *   - minify: Optimizasyon uygulanacak mı? (Aşağıda örneklendirilen optimizasyon methodlarını çağırır) (boolean)
 * 
 * minifyJavaScript için:
 *   - drop_console: true → Production'da console.log'ları tamamen kaldırır
 *   - mangle: { toplevel: true } → Değişken isimlerini en üst seviyede kısaltır
 *   - compress: { dead_code: true } → Kullanılmayan kodları temizler
 * 
 *   Terser Dökümantasyonu: https://terser.org/docs/api-reference
 *   Terser Compress Seçenekleri: https://terser.org/docs/options/#compress-options
 *   Terser Mangle Seçenekleri: https://terser.org/docs/options/#mangle-options
 * 
 * minifyCSS için:
 *   - mergeRules: true → Aynı selector'leri birleştirir
 *   - minifySelectors: true → Selector'leri optimize eder
 *   - reduceTransforms: true → Transform değerlerini sadeleştirir
 * 
 *   PostCSS Dökümantasyonu: https://postcss.org/
 *   cssnano Dökümantasyonu: https://cssnano.co/docs/what-are-optimisations/
 *   cssnano Preset Yapılandırması: https://cssnano.co/docs/presets/
 *
 * Nasıl Çalışır? (Basit Örnek)
 * ----------------------------
 * Kullanıcı "python serve.py" komutunu çalıştırdığında:
 * 
 *   1. serve.py → vendor dosyalarını kontrol eder
 *   2. Eksik dosya varsa → VendorManager.build_dependencies() çağrılır
 *   3. VendorManager → "npm run build" komutunu çalıştırır
 *   4. package.json → "build" scriptini bulur: "node build.js"
 *   5. build.js → dependencies.json'dan kütüphane listesini okur
 *   6. Her kütüphane için:
 *      - node_modules/ içinden dosyayı bulur
 *      - Minifikasyon uygular (gerekiyorsa)
 *      - vendor/ dizinine kopyalar
 *   7. Sonuç → vendor/ dizininde optimize edilmiş JS/CSS dosyaları
 * 
 * Çalışma Akışı:
 * --------------
 * 
 * 1. Python → Node.js Köprüsü:
 *    build.py/serve.py → VendorManager → npm run build → build.js
 *    - Python tarafından VendorManager.build_dependencies() ile tetiklenir
 *    - npm run build komutu package.json'daki script tanımını çalıştırır
 *    - build.js Node.js ortamında bağımsız olarak çalışır
 * 
 * 2. Dependency Yönetimi:
 *    dependencies.json → node_modules → vendor/
 *    - dependencies.json dosyasından konfigürasyon okunur
 *    - npm install ile node_modules'a kurulu paketler kullanılır
 *    - Optimize edilmiş ve gerekli dosyalar vendor/ dizinine kopyalanır
 * 
 * 3. Optimizasyon Süreci:
 *    Kaynak Dosya → Minifikasyon → Vendor Dizini
 *    - JavaScript: Terser ile minifikasyon
 *    - CSS: PostCSS + cssnano ile optimizasyon
 *    - Font dosyaları: Path düzeltmeleri ile kopyalama
 * 
 * Ana Özellikler:
 * ---------------
 * - Otomatik minifikasyon (zaten minified değilse)
 * - Font Awesome özel işleme (webfonts dizini)
 * 
 * Entegrasyon Noktaları:
 * ---------------------
 * - serve.py: check_vendor_files() ve build_vendor_files() fonksiyonları
 * - build.py: Vendor dosyalarının varlık kontrolü
 * - lib/docker.py: Volume mount hariç tutma (node_modules)
 * - config.json: Vendor dizin yolu konfigürasyonu
 * 
 * ========================================================
 * 
 * EN: Phantom Documentation Kit Vendor Builder (build.js)
 * ========================================================
 * 
 * This script is a critical component that manages JS/CSS dependencies for Phantom 
 * Documentation Kit. It optimizes JavaScript and CSS libraries used in modern web 
 * applications, aiming to provide a performant and reliable experience.
 * 
 * Important Notes
 * ---------------
 * The optimization capabilities offered by this script can be precisely tuned according to 
 * your project's unique requirements. The minifyJavaScript and minifyCSS methods leverage 
 * the powerful features of Terser and PostCSS to optimize your code. The current configuration 
 * provides a safe and balanced starting point, but you can customize these settings based on 
 * your project's needs.
 * 
 * Example usage scenarios:
 * 
 * dependencies.json configuration:
 *   {
 *     "dependencies": [
 *       {
 *         "name": "Chart.js",
 *         "from": "node_modules/chart.js/dist/chart.umd.js",
 *         "to": "chart.min.js",
 *         "type": "js",
 *         "minify": true
 *       },
 *       {
 *         "name": "Font Awesome CSS",
 *         "from": "node_modules/@fortawesome/fontawesome-free/css/all.css",
 *         "to": "fontawesome.min.css",
 *         "type": "css",
 *         "minify": true
 *       }
 *     ]
 *   }
 *   - name: Library name (for logging)
 *   - from: Source file path (in node_modules)
 *   - to: Target file name (in vendor/ directory)
 *   - type: File type ("js" or "css")
 *   - minify: Should apply optimization? (Calls the optimization methods exemplified below) (boolean)
 * 
 * For minifyJavaScript:
 *   - drop_console: true → Completely removes console.log statements in production
 *   - mangle: { toplevel: true } → Shortens variable names at the top level
 *   - compress: { dead_code: true } → Removes unused code
 * 
 *   Terser Documentation: https://terser.org/docs/api-reference
 *   Terser Compress Options: https://terser.org/docs/options/#compress-options
 *   Terser Mangle Options: https://terser.org/docs/options/#mangle-options
 * 
 * For minifyCSS:
 *   - mergeRules: true → Merges identical selectors
 *   - minifySelectors: true → Optimizes selectors
 *   - reduceTransforms: true → Simplifies transform values
 * 
 *   PostCSS Documentation: https://postcss.org/
 *   cssnano Documentation: https://cssnano.co/docs/what-are-optimisations/
 *   cssnano Preset Configuration: https://cssnano.co/docs/presets/
 * 
 * How It Works? (Simple Example)
 * ------------------------------
 * When a user runs "python serve.py":
 * 
 *   1. serve.py → checks vendor files
 *   2. If files are missing → VendorManager.build_dependencies() is called
 *   3. VendorManager → runs "npm run build" command
 *   4. package.json → finds "build" script: "node build.js"
 *   5. build.js → reads library list from dependencies.json
 *   6. For each library:
 *      - Finds the file from node_modules/
 *      - Applies minification (if needed)
 *      - Copies to vendor/ directory
 *   7. Result → optimized JS/CSS files in vendor/ directory
 * 
 * Workflow:
 * ---------
 * 
 * 1. Python → Node.js Bridge:
 *    build.py/serve.py → VendorManager → npm run build → build.js
 *    - Triggered by VendorManager.build_dependencies() from Python
 *    - npm run build executes the script definition in package.json
 *    - build.js runs independently in Node.js environment
 * 
 * 2. Dependency Management:
 *    dependencies.json → node_modules → vendor/
 *    - Configuration read from dependencies.json file
 *    - Uses packages installed in node_modules via npm install
 *    - Optimized and necessary files copied to vendor/ directory
 * 
 * 3. Optimization Process:
 *    Source File → Minification → Vendor Directory
 *    - JavaScript: Minification with Terser
 *    - CSS: Optimization with PostCSS + cssnano
 *    - Font files: Copy with path corrections
 * 
 * Key Features:
 * ------------
 * - Automatic minification (if not already minified)
 * - Special Font Awesome handling (webfonts directory)
 * 
 * Integration Points:
 * ------------------
 * - serve.py: check_vendor_files() and build_vendor_files() functions
 * - build.py: Vendor file existence check
 * - lib/docker.py: Volume mount exclusion (node_modules)
 * - config.json: Vendor directory path configuration
 * 
 */

const fs = require('fs');
const path = require('path');
const { minify } = require('terser');
const postcss = require('postcss');
const cssnano = require('cssnano');

// Load configuration
let CONFIG = {};
const CONFIG_FILE = path.resolve(__dirname, '../../config.json');
try {
  if (fs.existsSync(CONFIG_FILE)) {
    CONFIG = JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'));
  } else {
    console.error('[ERROR] Configuration file "config.json" not found!');
    console.error('Please ensure config.json exists in the project root.');
    process.exit(1);
  }
} catch (error) {
  console.error('[ERROR] Error reading config.json:', error.message);
  process.exit(1);
}

// Configuration
const VENDOR_DIR = path.resolve(__dirname, '../..', CONFIG['paths']['vendor_dir']);
const DEPENDENCIES_FILE = path.join(__dirname, 'dependencies.json');

// Built-in Font Awesome configuration
const FONT_AWESOME_CONFIG = {
  css: {
    name: "Font Awesome CSS (Built-in)",
    from: "node_modules/@fortawesome/fontawesome-free/css/all.min.css",
    to: "fontawesome-all.min.css",
    type: "css",
    minify: false // Already minified
  },
  webfonts: {
    name: "Font Awesome Webfonts (Built-in)",
    from: "node_modules/@fortawesome/fontawesome-free/webfonts",
    to: "webfonts"
  }
};

// Load dependencies from JSON file
let DEPENDENCIES = [];
try {
  const dependenciesData = JSON.parse(fs.readFileSync(DEPENDENCIES_FILE, 'utf8'));
  DEPENDENCIES = dependenciesData.dependencies;
  console.log(`[INFO] Loaded ${DEPENDENCIES.length} dependencies from dependencies.json`);
} catch (error) {
  console.error(`[ERROR] Error loading dependencies.json:`, error.message);
  process.exit(1);
}

// Utility functions
function ensureDirectoryExists(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
    console.log(`[INFO] Created directory: ${path.relative(process.cwd(), dir)}`);
  }
}


async function copyFile(source, destination, name, fileType, shouldMinify = null) {
  try {
    if (!fs.existsSync(source)) {
      console.error(`[ERROR] Source file not found: ${source}`);
      console.error(`   Make sure to run 'npm install' first`);
      return false;
    }

    let content = fs.readFileSync(source, 'utf8');
    const originalSize = (fs.statSync(source).size / 1024).toFixed(2);
    
    // Determine if we should minify
    const alreadyMinified = source.includes('.min.');
    const needsMinification = shouldMinify !== null ? shouldMinify : !alreadyMinified;
    
    // Apply minification if needed
    if (needsMinification && !alreadyMinified) {
      if (fileType === 'js') {
        console.log(`[INFO] Minifying ${name}...`);
        content = await minifyJavaScript(content, name);
        
        // Ensure minified files have .min extension
        if (!destination.endsWith('.min.js')) {
          destination = destination.replace('.js', '.min.js');
        }
      } else if (fileType === 'css') {
        console.log(`[INFO] Minifying ${name}...`);
        content = await minifyCSS(content, name);
        
        // Ensure minified files have .min extension
        if (!destination.endsWith('.min.css')) {
          destination = destination.replace('.css', '.min.css');
        }
      }
    }
    
    fs.writeFileSync(destination, content);
    const finalSize = (fs.statSync(destination).size / 1024).toFixed(2);
    
    if (needsMinification && !alreadyMinified) {
      const reduction = (((originalSize - finalSize) / originalSize) * 100).toFixed(1);
      console.log(`[SUCCESS] Copied and minified ${name} (${originalSize} KB -> ${finalSize} KB, -${reduction}%)`);
    } else {
      console.log(`[SUCCESS] Copied ${name} (${finalSize} KB)`);
    }
    
    return { success: true, finalPath: destination };
  } catch (error) {
    console.error(`[ERROR] Error copying ${name}:`, error.message);
    return { success: false };
  }
}
async function minifyJavaScript(content, filename) {
  try {
    const result = await minify(content, {
      compress: {
        drop_console: false,
        drop_debugger: true,
        pure_funcs: ['console.log']
      },
      mangle: {
        safari10: true
      },
      format: {
        comments: false
      }
    });

    if (result.error) {
      console.error(`[ERROR] Error minifying ${filename}:`, result.error);
      return content; // Return original content on error
    }

    return result.code;
  } catch (error) {
    console.error(`[ERROR] Error minifying ${filename}:`, error.message);
    return content; // Return original content on error
  }
}

async function minifyCSS(content, filename) {
  try {
    const result = await postcss([cssnano({
      preset: ['default', {
        discardComments: {
          removeAll: true
        },
        normalizeWhitespace: true,
        colormin: true,
        minifyFontValues: true,
        minifyGradients: true
      }]
    })]).process(content, { from: filename });
    
    return result.css;
  } catch (error) {
    console.error(`[ERROR] Error minifying ${filename}:`, error.message);
    return content; // Return original content on error
  }
}

function copyDirectory(source, destination, name) {
  try {
    if (!fs.existsSync(source)) {
      console.error(`[ERROR] Source directory not found: ${source}`);
      return false;
    }

    // Create destination directory
    ensureDirectoryExists(destination);

    // Copy all files recursively
    const files = fs.readdirSync(source);
    let copiedCount = 0;

    files.forEach(file => {
      const srcFile = path.join(source, file);
      const destFile = path.join(destination, file);
      
      if (fs.statSync(srcFile).isDirectory()) {
        copyDirectory(srcFile, destFile, `${name}/${file}`);
      } else {
        fs.copyFileSync(srcFile, destFile);
        copiedCount++;
      }
    });

    console.log(`[SUCCESS] Copied ${name} (${copiedCount} files)`);
    return true;
  } catch (error) {
    console.error(`[ERROR] Error copying ${name}:`, error.message);
    return false;
  }
}

// Process Font Awesome as built-in dependency
async function processFontAwesome() {
  console.log('\n[INFO] Processing Font Awesome (Built-in)...');
  
  // 1. Copy and process Font Awesome CSS
  const cssSourcePath = path.join(__dirname, FONT_AWESOME_CONFIG.css.from);
  const cssDestPath = path.join(VENDOR_DIR, FONT_AWESOME_CONFIG.css.to);
  
  const cssResult = await copyFile(
    cssSourcePath, 
    cssDestPath, 
    FONT_AWESOME_CONFIG.css.name, 
    FONT_AWESOME_CONFIG.css.type, 
    FONT_AWESOME_CONFIG.css.minify
  );
  
  if (cssResult.success) {
    // Fix Font Awesome CSS paths
    console.log('[INFO] Fixing Font Awesome font paths...');
    try {
      let cssContent = fs.readFileSync(cssResult.finalPath, 'utf8');
      // Replace ../webfonts/ with ./webfonts/ since CSS and fonts are in same vendor directory
      cssContent = cssContent.replace(/\.\.\/webfonts\//g, './webfonts/');
      fs.writeFileSync(cssResult.finalPath, cssContent);
      console.log('[SUCCESS] Font paths fixed in CSS');
    } catch (error) {
      console.error('[ERROR] Error fixing font paths:', error.message);
    }
  }
  
  // 2. Copy Font Awesome webfonts
  const webfontsSourcePath = path.join(__dirname, FONT_AWESOME_CONFIG.webfonts.from);
  const webfontsDestPath = path.join(VENDOR_DIR, FONT_AWESOME_CONFIG.webfonts.to);
  
  if (fs.existsSync(webfontsSourcePath)) {
    if (copyDirectory(webfontsSourcePath, webfontsDestPath, FONT_AWESOME_CONFIG.webfonts.name)) {
      console.log('[SUCCESS] Font Awesome processing completed');
      return true;
    }
  } else {
    console.error('[ERROR] Font Awesome webfonts directory not found');
    return false;
  }
  
  return cssResult.success;
}

// Main build process
async function build() {
  console.log('[BUILD] Building vendor dependencies for Phantom Documentation Kit...\n');

  // Ensure vendor directory exists
  ensureDirectoryExists(VENDOR_DIR);

  let successCount = 0;

  // Copy each dependency (excluding Font Awesome as it's now built-in)
  for (const dep of DEPENDENCIES) {
    const sourcePath = path.join(__dirname, dep.from);
    const destPath = path.join(VENDOR_DIR, dep.to);

    const result = await copyFile(sourcePath, destPath, dep.name, dep.type, dep.minify);
    if (result.success) {
      successCount++;
    }
  }

  // Process Font Awesome as built-in dependency
  const fontAwesomeSuccess = await processFontAwesome();
  if (fontAwesomeSuccess) {
    successCount++;
  }

  // Summary
  console.log(`\n[SUMMARY] Build Summary:`);
  console.log(`   Successfully copied: ${successCount}/${DEPENDENCIES.length + 1} items`); // +1 for Font Awesome
  console.log(`   Output directory: ${path.relative(process.cwd(), VENDOR_DIR)}`);

  if (successCount < DEPENDENCIES.length + 1) { // +1 for Font Awesome
    console.log(`\n[WARNING] Some files could not be copied. Please check the errors above.`);
    process.exit(1);
  } else {
    console.log(`\n[SUCCESS] Vendor build completed successfully!`);
  }
}

// Check if node_modules exists
if (!fs.existsSync(path.join(__dirname, 'node_modules'))) {
  console.error('[ERROR] node_modules not found!');
  console.error('   Please run: npm install');
  console.error('   From directory:', __dirname);
  process.exit(1);
}

// Run build
build().catch(error => {
  console.error(`[ERROR] Build failed with error:`, error);
  process.exit(1);
});