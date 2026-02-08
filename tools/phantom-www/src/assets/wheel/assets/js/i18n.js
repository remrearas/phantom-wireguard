// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
 * ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
 * ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
 * ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
 * ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
 * ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
 *
 * Phantom-WG — Spin & Deploy (i18n Loader)
 *
 * Copyright (C) 2025 Riza Emre ARAS <r.emrearas@proton.me>
 *
 * This file is part of Phantom-WG.
 *
 * Phantom-WG is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <https://www.gnu.org/licenses/>.
 */

(function () {
  'use strict';

  // Initialise WHEEL_LANG as an empty object so wheel.js can grab a
  // reference to it synchronously. Properties are filled in once
  // languages.json has been fetched via Object.assign (same reference).
  window.WHEEL_LANG = {};

  const lang = document.documentElement.lang || 'en';

  fetch('data/languages.json')
    .then(function (res) { return res.json(); })
    .then(function (data) {
      const strings = data[lang] || data['en'];
      Object.assign(window.WHEEL_LANG, strings);
      applyDOM(strings);
    })
    .catch(function () {
      console.warn('[i18n] languages.json could not be loaded — using HTML defaults');
    });

  function applyDOM(strings) {
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      const key = el.getAttribute('data-i18n');
      if (strings[key] !== undefined) el.textContent = strings[key];
    });

    document.querySelectorAll('[data-i18n-href]').forEach(function (el) {
      const key = el.getAttribute('data-i18n-href');
      if (strings[key] !== undefined) el.href = strings[key];
    });
  }
})();
