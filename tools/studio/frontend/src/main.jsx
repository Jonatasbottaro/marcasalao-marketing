import React from 'react';
import { createRoot } from 'react-dom/client';
import { LayerProvider } from '@astryxdesign/core';
import { Theme } from '@astryxdesign/core/theme';
import { neutralTheme } from '@astryxdesign/theme-neutral/built';
import './styles/studio-astryx.css';
import { WorksAndProjectsTab } from './components/WorksAndProjectsTab.jsx';

function mountAstryxHomePilot() {
  const container = document.getElementById('home-astryx-root');
  if (!container) return;

  const legacyRoot = document.getElementById('home-legacy-root');
  if (legacyRoot) {
    legacyRoot.hidden = true;
    legacyRoot.innerHTML = '';
  }

  window.__studioAstryxHomeActive = true;

  createRoot(container).render(
    <React.StrictMode>
      <Theme theme={neutralTheme}>
        <LayerProvider>
          <WorksAndProjectsTab />
        </LayerProvider>
      </Theme>
    </React.StrictMode>,
  );
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mountAstryxHomePilot, { once: true });
} else {
  mountAstryxHomePilot();
}
