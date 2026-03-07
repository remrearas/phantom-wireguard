// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 *  █████╗ ██████╗  █████╗ ███████╗
 * ██╔══██╗██╔══██╗██╔══██╗██╔════╝
 * ███████║██████╔╝███████║███████╗
 * ██╔══██║██╔══██╗██╔══██║╚════██║
 * ██║  ██║██║  ██║██║  ██║███████║
 * ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝
 *
 * Copyright (C) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
 *
 * This file is part of ARTEK Homepage.
 *
 * ARTEK Homepage is free software: you can redistribute it and/or modify
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

/**
 * Carbon Icon Mapping for Sprite Themes
 * Maps theme sprite types to Carbon React Icons
 */

import {
  BareMetalServer,
  WarningAlt,
  Cloud as CloudIcon,
  Rocket,
  CloudDataOps,
  Running,
  Document,
  Roadmap,
  TrafficCone,
  Construction,
  Building,
} from '@carbon/icons-react';
import type { CarbonIconType } from '@carbon/icons-react';
import type { ThemeName } from './types';

export type IconComponent = CarbonIconType;

export interface ThemeIcons {
  dino: IconComponent;
  obstacles: IconComponent[];
  clouds: IconComponent[];
}

const ERROR_ICONS: ThemeIcons = {
  dino: BareMetalServer,
  obstacles: [WarningAlt, WarningAlt, WarningAlt],
  clouds: [CloudIcon, CloudIcon, CloudIcon],
};

const CONSULTANCY_ICONS: ThemeIcons = {
  dino: Running,
  obstacles: [Document, WarningAlt, Roadmap],
  clouds: [Rocket, CloudIcon, CloudDataOps],
};

const UNDER_CONSTRUCTION_ICONS: ThemeIcons = {
  dino: Running,
  obstacles: [Construction, TrafficCone, Building],
  clouds: [CloudIcon, CloudIcon, CloudIcon],
};

export function getThemeIcons(theme: ThemeName): ThemeIcons {
  switch (theme) {
    case 'consultancy':
      return CONSULTANCY_ICONS;
    case 'under-construction':
      return UNDER_CONSTRUCTION_ICONS;
    case 'error':
    default:
      return ERROR_ICONS;
  }
}

export interface VariantCounts {
  obstacle: number;
  cloud: number;
}

export function getVariantCounts(themeIcons: ThemeIcons): VariantCounts {
  return {
    obstacle: themeIcons.obstacles.length,
    cloud: themeIcons.clouds.length,
  };
}
