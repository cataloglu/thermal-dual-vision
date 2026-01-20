/**
 * Zones tab - Detection zones (placeholder for future)
 */
import React from 'react';

export const ZonesTab: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">Detection Zones</h3>
        <p className="text-sm text-muted mb-6">
          Configure polygon zones for motion and person detection filtering
        </p>
      </div>

      <div className="p-8 bg-surface2 border border-border rounded-lg text-center">
        <p className="text-muted">
          Zone configuration will be available in a future update
        </p>
        <p className="text-sm text-muted mt-2">
          Coming soon: Visual polygon editor
        </p>
      </div>
    </div>
  );
};
