import type { UserProfile } from '../types';

interface PresetProfile extends UserProfile {
  id: string;
  label: string;
  description: string;
}

export const PROFILE_PRESETS: PresetProfile[] = [
  {
    id: 'default',
    label: 'Default user',
    description: 'No declared accessibility needs.',
    assistive_tech: false,
    visual_pref: 0.0,
    motor_pref: 0.0,
    cognitive_pref: 0.0,
  },
  {
    id: 'low_vision',
    label: 'Low vision',
    description: 'Higher contrast and larger fonts preferred.',
    assistive_tech: false,
    visual_pref: 0.8,
    motor_pref: 0.0,
    cognitive_pref: 0.0,
    vulnerable: true,
  },
  {
    id: 'screen_reader',
    label: 'Screen reader user',
    description: 'Uses assistive technology; layout stability matters.',
    assistive_tech: true,
    visual_pref: 0.6,
    motor_pref: 0.2,
    cognitive_pref: 0.0,
    vulnerable: true,
  },
  {
    id: 'motor',
    label: 'Motor impairment',
    description: 'Larger hit targets, reduced motion preferred.',
    assistive_tech: false,
    visual_pref: 0.1,
    motor_pref: 0.85,
    cognitive_pref: 0.1,
    reduced_motion_preferred: true,
    vulnerable: true,
  },
  {
    id: 'cognitive',
    label: 'Cognitive accommodations',
    description: 'Simplified layouts and reduced motion.',
    assistive_tech: false,
    visual_pref: 0.2,
    motor_pref: 0.2,
    cognitive_pref: 0.8,
    reduced_motion_preferred: true,
    vulnerable: true,
  },
];

interface Props {
  selectedId: string;
  onChange(profile: PresetProfile): void;
}

export default function ProfilePicker({ selectedId, onChange }: Props) {
  return (
    <div className="card stack" aria-labelledby="profile-picker-h">
      <h3 id="profile-picker-h">Simulated user profile</h3>
      <p className="muted" style={{ margin: 0 }}>
        Drives the user-profile features (visual_pref, motor_pref, etc.) sent in
        every context payload. Switch profiles to see different policies and
        HITL triggers.
      </p>
      <div className="row" role="radiogroup" aria-label="User profile preset">
        {PROFILE_PRESETS.map((p) => {
          const active = p.id === selectedId;
          return (
            <button
              key={p.id}
              role="radio"
              aria-checked={active}
              className={active ? 'primary' : ''}
              onClick={() => onChange(p)}
            >
              {p.label}
            </button>
          );
        })}
      </div>
      <p className="muted" style={{ margin: 0 }}>
        {PROFILE_PRESETS.find((p) => p.id === selectedId)?.description}
      </p>
    </div>
  );
}
