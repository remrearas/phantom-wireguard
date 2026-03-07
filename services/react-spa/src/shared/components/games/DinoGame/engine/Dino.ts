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

import type { BoundingBox, GameConfig } from '../types';
import { DINO, GAME_AREA } from '../constants';

export class Dino {
  private readonly x: number;
  private y: number;
  private velocityY: number;
  private jumping: boolean;
  private readonly groundY: number;

  constructor(config: GameConfig) {
    this.x = DINO.INIT_X;
    this.groundY = GAME_AREA.HEIGHT - DINO.HEIGHT - config.groundY;
    this.y = this.groundY;
    this.velocityY = 0;
    this.jumping = false;
  }

  jump(jumpVelocity: number): void {
    if (!this.jumping) {
      this.velocityY = jumpVelocity;
      this.jumping = true;
    }
  }

  update(gravity: number): void {
    if (this.jumping) {
      this.velocityY += gravity;
      this.y += this.velocityY;

      // Landed
      if (this.y >= this.groundY) {
        this.y = this.groundY;
        this.velocityY = 0;
        this.jumping = false;
      }
    }
  }

  getBoundingBox(): BoundingBox {
    return {
      x: this.x + 5, // Slight padding for more forgiving collision
      y: this.y + 5,
      width: DINO.WIDTH - 10,
      height: DINO.HEIGHT - 10,
    };
  }

  reset(): void {
    this.y = this.groundY;
    this.velocityY = 0;
    this.jumping = false;
  }
}
