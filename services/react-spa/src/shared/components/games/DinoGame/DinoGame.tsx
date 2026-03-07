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

import React, { useEffect, useRef, useState, useMemo, lazy, Suspense } from 'react';
import { Grid, Column } from '@carbon/react';
import LoadingSpinner from '@shared/components/ui/LoadingSpinner';
import { GameEngine, type GameRenderState } from './engine/GameEngine';
import { GameState } from './types';
import { useKeyboardInput } from './hooks/useKeyboardInput';
import { useLocale } from '@shared/hooks';
import { translate } from '@shared/translations';
import { getThemeIcons, getVariantCounts } from './assets/themes/iconMap';
import type { ThemeName } from './assets/themes';
import { GAME_AREA } from './constants';
import './styles/DinoGame.scss';

export interface DinoGameProps {
  theme?: ThemeName;
}

const DinoGame: React.FC<DinoGameProps> = ({ theme = 'error' }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [gameEngine, setGameEngine] = useState<GameEngine | null>(null);
  const [renderState, setRenderState] = useState<GameRenderState | null>(null);
  const { locale } = useLocale();
  const t = translate(locale);
  const themeIcons = useMemo(() => getThemeIcons(theme), [theme]);
  const variantCounts = useMemo(() => getVariantCounts(themeIcons), [themeIcons]);

  const messages = useMemo(
    () => ({
      startMessage: t.dinoGame.startMessage,
      gameOver: t.dinoGame.gameOver,
      restartMessage: t.dinoGame.restartMessage,
      score: t.dinoGame.score,
    }),
    [t]
  );

  // Initialize game engine with dynamic variant counts from theme
  useEffect(() => {
    const engine = new GameEngine(messages, variantCounts);
    setGameEngine(engine);
    setRenderState(engine.getState());

    return () => {
      setGameEngine(null);
    };
  }, [messages, variantCounts]);

  // Update render state on each frame
  useEffect(() => {
    if (!gameEngine) return;

    let animationId: number;
    const gameLoop = () => {
      gameEngine.update();
      setRenderState(gameEngine.getState());
      animationId = requestAnimationFrame(gameLoop);
    };

    animationId = requestAnimationFrame(gameLoop);

    return () => {
      if (animationId) cancelAnimationFrame(animationId);
    };
  }, [gameEngine]);

  // Setup keyboard input (only when visible in viewport)
  // ArrowUp only captured during RUNNING state to avoid hijacking page scroll
  useKeyboardInput(gameEngine, containerRef, renderState?.state ?? GameState.WAITING);

  // Setup touch input
  useEffect(() => {
    if (!gameEngine || !containerRef.current) return;

    const container = containerRef.current;
    const handleInteraction = (e: Event) => {
      e.preventDefault();
      gameEngine.jump();
    };

    container.addEventListener('click', handleInteraction);
    container.addEventListener('touchstart', handleInteraction, { passive: false });

    return () => {
      container.removeEventListener('click', handleInteraction);
      container.removeEventListener('touchstart', handleInteraction);
    };
  }, [gameEngine]);

  if (!renderState) {
    return null;
  }

  const DinoIcon = themeIcons.dino;

  return (
    <Grid>
      <Column sm={4} md={8} lg={16}>
        <div
          ref={containerRef}
          className="dino-game"
          style={{
            position: 'relative',
            height: `${GAME_AREA.HEIGHT}px`,
            width: `${GAME_AREA.WIDTH}px`,
            maxWidth: '100%',
            margin: '0 auto',
          }}
        >
          {/* Ground line */}
          <div className="dino-game__ground" />

          {/* Clouds */}
          {renderState.clouds.map((cloud, idx) => {
            const CloudIcon = themeIcons.clouds[cloud.variantIndex] || themeIcons.clouds[0];
            return (
              <div
                key={`cloud-${idx}`}
                className="dino-game__cloud"
                style={{
                  transform: `translate(${cloud.x}px, ${cloud.y}px)`,
                  width: `${cloud.width}px`,
                  height: `${cloud.height}px`,
                }}
              >
                <CloudIcon size={cloud.width} className="dino-game__icon dino-game__icon--cloud" />
              </div>
            );
          })}

          {/* Dino */}
          <div
            className="dino-game__dino"
            style={{
              transform: `translate(${renderState.dino.x}px, ${renderState.dino.y}px)`,
              width: `${renderState.dino.width}px`,
              height: `${renderState.dino.height}px`,
            }}
          >
            <DinoIcon
              size={renderState.dino.width}
              className="dino-game__icon dino-game__icon--dino"
            />
          </div>

          {/* Obstacles */}
          {renderState.obstacles.map((obstacle, idx) => {
            const ObstacleIcon =
              themeIcons.obstacles[obstacle.variantIndex] || themeIcons.obstacles[0];
            return (
              <div
                key={`obstacle-${idx}`}
                className="dino-game__obstacle"
                style={{
                  transform: `translate(${obstacle.x}px, ${obstacle.y}px)`,
                  width: `${obstacle.width}px`,
                  height: `${obstacle.height}px`,
                }}
              >
                <ObstacleIcon
                  size={obstacle.width}
                  className="dino-game__icon dino-game__icon--obstacle"
                />
              </div>
            );
          })}

          {/* Score */}
          <div className="dino-game__score">{String(renderState.score).padStart(5, '0')}</div>

          {/* Messages */}
          {renderState.state === GameState.WAITING && (
            <div className="dino-game__message">{renderState.messages.startMessage}</div>
          )}
          {renderState.state === GameState.CRASHED && (
            <div className="dino-game__message">
              <div className="dino-game__message-title">{renderState.messages.gameOver}</div>
              <div className="dino-game__message-subtitle">
                {renderState.messages.restartMessage}
              </div>
            </div>
          )}
        </div>
      </Column>
    </Grid>
  );
};

// Lazy-loaded version with built-in Suspense boundary, LoadingSpinner, and SSR safety
const LazyDinoGameComponent = lazy(() => Promise.resolve({ default: DinoGame }));

const LazyDinoGame: React.FC<DinoGameProps> = (props) => {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <LazyDinoGameComponent {...props} />
    </Suspense>
  );
};

// Composition pattern: Attach Lazy as a property
interface DinoGameComponent extends React.FC<DinoGameProps> {
  Lazy: React.FC<DinoGameProps>;
}

const DinoGameWithLazy = Object.assign(DinoGame, {
  Lazy: LazyDinoGame,
}) as DinoGameComponent;

export default DinoGameWithLazy;
