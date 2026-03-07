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

import { useEffect, useState, RefObject } from 'react';
import type { GameEngine } from '../engine/GameEngine';
import { GameState } from '../types';

export function useKeyboardInput(
  gameEngine: GameEngine | null,
  containerRef: RefObject<HTMLElement | null>,
  gameState: GameState
) {
  // Start with true - assume visible until observer confirms otherwise
  const [isVisible, setIsVisible] = useState(true);

  // Track viewport visibility with Intersection Observer
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new IntersectionObserver(([entry]) => setIsVisible(entry.isIntersecting), {
      threshold: 1,
    });

    observer.observe(container);

    return () => observer.disconnect();
  }, [containerRef]);

  // Keyboard controls - ArrowUp only during RUNNING state (no Space to avoid AI chat widget conflict)
  // Game start/restart is handled by TAP/CLICK only
  useEffect(() => {
    if (!gameEngine || !isVisible) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // ArrowUp only works during active gameplay for jumping
      if (e.code === 'ArrowUp' && gameState === GameState.RUNNING) {
        e.preventDefault();
        gameEngine.jump();
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [gameEngine, isVisible, gameState]);
}
