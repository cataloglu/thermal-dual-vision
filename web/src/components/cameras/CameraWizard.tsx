import { h } from 'preact';
import { useMemo, useState } from 'preact/hooks';
import { Card } from '../ui/Card';
import { Camera, CameraTestResponse, createCamera, testCameraPayload } from '../../utils/api';
import { redactRtspUrl } from '../../utils/redact';

interface CameraWizardProps {
  onClose: () => void;
  onSaved: () => void;
}

type CameraType = 'color' | 'thermal' | 'dual';

export function CameraWizard({ onClose, onSaved }: CameraWizardProps) {
  const [step, setStep] = useState(1);
  const [name, setName] = useState('');
  const [type, setType] = useState<CameraType>('color');
  const [host, setHost] = useState('');
  const [port, setPort] = useState('554');
  const [user, setUser] = useState('');
  const [pass, setPass] = useState('');
  const [channelColor, setChannelColor] = useState('102');
  const [channelThermal, setChannelThermal] = useState('202');
  const [testResult, setTestResult] = useState<CameraTestResponse | null>(null);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const rtspBase = useMemo(() => {
    if (!host) {
      return '';
    }
    const credentials = user ? `${user}:${pass || '***'}@` : '';
    return `rtsp://${credentials}${host}:${port}`;
  }, [host, port, user, pass]);

  const buildUrl = (channel: string, masked = false) => {
    if (!host) return '';
    const credentials = user ? `${user}:${masked ? '***' : pass}@` : '';
    return `rtsp://${credentials}${host}:${port}/Streaming/Channels/${channel}`;
  };

  const payload = useMemo<Partial<Camera>>(
    () => ({
      name,
      type,
      rtsp_url_color: type === 'thermal' ? '' : buildUrl(channelColor),
      rtsp_url_thermal: type === 'color' ? '' : buildUrl(channelThermal),
      channel_color: Number(channelColor),
      channel_thermal: Number(channelThermal),
    }),
    [name, type, channelColor, channelThermal, host, port, user, pass]
  );

  const testConnection = async () => {
    setTesting(true);
    setError(null);
    setTestResult(null);
    try {
      const result = await testCameraPayload(payload);
      setTestResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Test failed');
    } finally {
      setTesting(false);
    }
  };

  const saveCamera = async () => {
    setSaving(true);
    setError(null);
    try {
      await createCamera(payload);
      onSaved();
      setStep(5);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const canContinue = () => {
    if (step === 1) return true;
    if (step === 2) return Boolean(name && host);
    return true;
  };

  return (
    <Card title="Add Camera Wizard">
      <div class="space-y-6">
        {step === 1 && (
          <div class="space-y-4">
            <h3 class="text-lg font-semibold">Step 1: Select Camera Type</h3>
            <div class="space-y-2">
              {(['color', 'thermal', 'dual'] as CameraType[]).map((value) => (
                <label class="flex items-center gap-2" key={value}>
                  <input
                    type="radio"
                    name="cameraType"
                    value={value}
                    checked={type === value}
                    onChange={() => setType(value)}
                  />
                  <span class="capitalize">{value}</span>
                </label>
              ))}
            </div>
          </div>
        )}

        {step === 2 && (
          <div class="space-y-4">
            <h3 class="text-lg font-semibold">Step 2: RTSP Details</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="text-sm text-gray-600 dark:text-gray-400">Camera Name</label>
                <input
                  value={name}
                  onInput={(e) => setName((e.target as HTMLInputElement).value)}
                  class="w-full mt-1 px-3 py-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
                  placeholder="Lobby Camera"
                />
              </div>
              <div>
                <label class="text-sm text-gray-600 dark:text-gray-400">Host / IP</label>
                <input
                  value={host}
                  onInput={(e) => setHost((e.target as HTMLInputElement).value)}
                  class="w-full mt-1 px-3 py-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
                  placeholder="192.168.1.10"
                />
              </div>
              <div>
                <label class="text-sm text-gray-600 dark:text-gray-400">Port</label>
                <input
                  value={port}
                  onInput={(e) => setPort((e.target as HTMLInputElement).value)}
                  class="w-full mt-1 px-3 py-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
                />
              </div>
              <div>
                <label class="text-sm text-gray-600 dark:text-gray-400">User</label>
                <input
                  value={user}
                  onInput={(e) => setUser((e.target as HTMLInputElement).value)}
                  class="w-full mt-1 px-3 py-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
                />
              </div>
              <div>
                <label class="text-sm text-gray-600 dark:text-gray-400">Password</label>
                <input
                  type="password"
                  value={pass}
                  onInput={(e) => setPass((e.target as HTMLInputElement).value)}
                  class="w-full mt-1 px-3 py-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
                />
              </div>
              <div>
                <label class="text-sm text-gray-600 dark:text-gray-400">Color Channel</label>
                <input
                  value={channelColor}
                  onInput={(e) => setChannelColor((e.target as HTMLInputElement).value)}
                  class="w-full mt-1 px-3 py-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
                />
              </div>
              {type !== 'color' && (
                <div>
                  <label class="text-sm text-gray-600 dark:text-gray-400">Thermal Channel</label>
                  <input
                    value={channelThermal}
                    onInput={(e) => setChannelThermal((e.target as HTMLInputElement).value)}
                    class="w-full mt-1 px-3 py-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
                  />
                </div>
              )}
            </div>
            <div class="text-sm text-gray-500 dark:text-gray-400">
              Hikvision default: <code>{redactRtspUrl(rtspBase)}/Streaming/Channels/102</code> (color),{' '}
              <code>{redactRtspUrl(rtspBase)}/Streaming/Channels/202</code> (thermal)
            </div>
            <div class="space-y-1 text-sm text-gray-600 dark:text-gray-400">
              <div>Preview (masked):</div>
              <div>{redactRtspUrl(buildUrl(channelColor, true)) || '—'}</div>
              {type !== 'color' && <div>{redactRtspUrl(buildUrl(channelThermal, true)) || '—'}</div>}
            </div>
          </div>
        )}

        {step === 3 && (
          <div class="space-y-4">
            <h3 class="text-lg font-semibold">Step 3: Test Connection</h3>
            <button
              onClick={testConnection}
              disabled={testing}
              class="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {testing ? 'Testing...' : 'Test connection'}
            </button>
            {testResult?.ok && testResult.snapshot && (
              <img
                src={`data:image/jpeg;base64,${testResult.snapshot}`}
                alt="Camera snapshot"
                class="max-w-full rounded border border-gray-200 dark:border-gray-700"
              />
            )}
            {testResult?.ok === false && (
              <p class="text-red-600 dark:text-red-400">Test failed: {testResult.error}</p>
            )}
            {error && <p class="text-red-600 dark:text-red-400">{error}</p>}
          </div>
        )}

        {step === 4 && (
          <div class="space-y-3">
            <h3 class="text-lg font-semibold">Step 4: Preset Suggestions</h3>
            <ul class="list-disc pl-6 text-sm text-gray-600 dark:text-gray-400 space-y-1">
              {type === 'thermal' && <li>Thermal preset: lower sensitivity, higher threshold.</li>}
              {type === 'color' && <li>Color preset: medium sensitivity, default thresholds.</li>}
              {type === 'dual' && <li>Dual preset: sync tolerance 150-500 ms.</li>}
            </ul>
          </div>
        )}

        {step === 5 && (
          <div class="space-y-3">
            <h3 class="text-lg font-semibold">Camera Saved</h3>
            <p class="text-sm text-gray-600 dark:text-gray-400">
              Camera saved. Restart the pipeline to apply changes.
            </p>
          </div>
        )}

        {error && step !== 3 && <p class="text-red-600 dark:text-red-400">{error}</p>}

        <div class="flex items-center justify-between">
          <button
            onClick={onClose}
            class="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700"
          >
            Cancel
          </button>
          <div class="flex gap-2">
            {step > 1 && step < 5 && (
              <button
                onClick={() => setStep(step - 1)}
                class="px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg"
              >
                Back
              </button>
            )}
            {step < 4 && (
              <button
                onClick={() => setStep(step + 1)}
                disabled={!canContinue()}
                class="px-3 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors disabled:opacity-50"
              >
                Next
              </button>
            )}
            {step === 4 && (
              <button
                onClick={saveCamera}
                disabled={saving}
                class="px-3 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save camera'}
              </button>
            )}
            {step === 5 && (
              <button
                onClick={onClose}
                class="px-3 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
              >
                Done
              </button>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}
