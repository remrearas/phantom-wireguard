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

import type { GameConfig } from './types';

export const GAME_CONFIG: GameConfig = {
  gravity: 0.5, // Downward acceleration per frame (px/frame²)
  speed: 6, // Initial horizontal scroll speed (px/frame)
  maxSpeed: 13, // Maximum scroll speed cap (px/frame)
  acceleration: 0.001, // Speed increase per frame (px/frame²)
  jumpVelocity: -10, // Initial upward velocity on jump (px/frame, negative = up)
  groundY: 0, // Ground level offset from bottom (px)
};

export const GAME_AREA = {
  WIDTH: 600, // Game viewport width (px)
  HEIGHT: 200, // Game viewport height (px)
};

export const DINO = {
  WIDTH: 48, // Dino sprite width (px)
  HEIGHT: 48, // Dino sprite height (px)
  INIT_X: 50, // Dino horizontal position from left (px)
};

export const OBSTACLE = {
  WIDTH: 40, // Obstacle sprite width (px)
  HEIGHT: 40, // Obstacle sprite height (px)
  GAP_MIN: 400, // Minimum distance between obstacles (px)
  GAP_MAX: 700, // Maximum distance between obstacles (px)
};

export const CLOUD = {
  WIDTH: 32, // Cloud sprite width (px)
  HEIGHT: 32, // Cloud sprite height (px)
  GAP_MIN: 100, // Minimum horizontal gap between clouds (px)
  GAP_MAX: 400, // Maximum horizontal gap between clouds (px)
  Y_MIN: 20, // Minimum cloud height from top (px)
  Y_MAX: 60, // Maximum cloud height from top (px)
};
