import React from 'react';
import { createRoot } from 'react-dom/client';
import { LayerProvider } from '@astryxdesign/core';
import { Theme } from '@astryxdesign/core/theme';
import { neutralTheme } from '@astryxdesign/theme-neutral/built';
import './styles/studio-astryx.css';
import { WorksAndProjectsTab } from './components/WorksAndProjectsTab.jsx';
import { ProductionQueueTab } from './components/ProductionQueueTab.jsx';
import { ReviewPackagePanel } from './components/ReviewPackagePanel.jsx';

function mountAstryxTab({ containerId, legacyId, flagName, Component }) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.dataset.astryxReady = '1';
  window[flagName] = true;

  const legacyRoot = document.getElementById(legacyId);
  if (legacyRoot) {
    legacyRoot.hidden = true;
    legacyRoot.innerHTML = '';
  }

  createRoot(container).render(
    <React.StrictMode>
      <Theme theme={neutralTheme}>
        <LayerProvider>
          <Component />
        </LayerProvider>
      </Theme>
    </React.StrictMode>,
  );
}

function mountAstryxStudioPilots() {
  mountAstryxTab({
    containerId: 'home-astryx-root',
    legacyId: 'home-legacy-root',
    flagName: '__studioAstryxHomeActive',
    Component: WorksAndProjectsTab,
  });
  mountAstryxTab({
    containerId: 'queue-astryx-root',
    legacyId: 'queue-legacy-root',
    flagName: '__studioAstryxQueueActive',
    Component: ProductionQueueTab,
  });
  mountAstryxTab({
    containerId: 'review-package-astryx-root',
    legacyId: 'review-package-legacy-root',
    flagName: '__studioAstryxReviewPackageActive',
    Component: ReviewPackagePanel,
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mountAstryxStudioPilots, { once: true });
} else {
  mountAstryxStudioPilots();
}
