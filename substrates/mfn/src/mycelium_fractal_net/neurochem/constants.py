"""Named constants for neuromodulation kinetics.

Every constant has a name, value, and provenance. No bare float literals
in kinetics.py except 0.0 and 1.0.

Provenance key:
    [LIT]  — from published literature with DOI
    [CAL]  — calibrated via validation/neurochem_controls.py
    [PHYS] — derived from biophysical first principles
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════
#  Occupancy bias weights for excitability offset
#  [CAL] Relative contribution of each receptor state to
#  local excitability. Active receptors increase inhibition,
#  resting provide baseline tone, desensitized reduce drive.
#  Calibrated against gabaa_tonic_muscimol_alpha1beta3 profile.
# ═══════════════════════════════════════════════════════════════

OCCUPANCY_ACTIVE_WEIGHT: float = 0.60  # [CAL] Active state contribution
OCCUPANCY_RESTING_WEIGHT: float = 0.25  # [CAL] Resting state contribution
OCCUPANCY_DESENSITIZED_WEIGHT: float = -0.15  # [CAL] Desensitized state penalty

# ═══════════════════════════════════════════════════════════════
#  Excitability drive
#  [PHYS] Maps centered activator to [0, 1] excitability range.
#  Linear transform: drive = 0.5 + scale * centered_activator
# ═══════════════════════════════════════════════════════════════

EXCITABILITY_DRIVE_OFFSET: float = 0.5  # [PHYS] Baseline drive at zero activator
EXCITABILITY_DRIVE_SCALE: float = 2.0  # [PHYS] Sensitivity to activator deviation

# ═══════════════════════════════════════════════════════════════
#  Occupancy bias modulation of rest offset
#  [CAL] How much excitability drive modulates the rest offset
#  effect. 0.5 + 0.5*drive means half is baseline, half is
#  activity-dependent.
# ═══════════════════════════════════════════════════════════════

REST_OFFSET_BASELINE_FRACTION: float = 0.50  # [CAL] Fraction independent of drive
REST_OFFSET_DRIVE_FRACTION: float = 0.50  # [CAL] Fraction modulated by drive

# ═══════════════════════════════════════════════════════════════
#  Plasticity contribution to excitability
#  [LIT] When plasticity_scale > 1.0, additional offset from
#  plasticity index. 0.10 = 10% of rest_offset per unit plasticity.
#  Ref: Bhatt et al. 2021, doi:10.1073/pnas.2026596118
# ═══════════════════════════════════════════════════════════════

PLASTICITY_EXCITABILITY_FRACTION: float = 0.10  # [LIT] Bhatt et al. 2021

# ═══════════════════════════════════════════════════════════════
#  Excitability offset clamp
#  [PHYS] Maximum local excitability offset ±2 mV.
#  Beyond this, the offset is non-physiological for subthreshold.
# ═══════════════════════════════════════════════════════════════

EXCITABILITY_OFFSET_MAX_MV: float = 2.0  # [PHYS] Max offset magnitude in mV

# ═══════════════════════════════════════════════════════════════
#  Field drive normalization
#  [PHYS] Converts membrane potential to [0, 1] drive signal.
#  Assumes resting potential ~-70mV, threshold ~+40mV.
#  drive = (V + 70mV) / 110mV
# ═══════════════════════════════════════════════════════════════

FIELD_DRIVE_REST_V: float = 0.070  # [PHYS] Resting potential offset (70 mV)
FIELD_DRIVE_RANGE_V: float = 0.110  # [PHYS] Full range: -70mV to +40mV = 110mV

# ═══════════════════════════════════════════════════════════════
#  Activity drive mixing
#  [CAL] Combines activator and field drive into single signal.
# ═══════════════════════════════════════════════════════════════

ACTIVITY_DRIVE_ACTIVATOR_WEIGHT: float = 0.5  # [CAL] Activator contribution
ACTIVITY_DRIVE_FIELD_WEIGHT: float = 0.5  # [CAL] Field drive contribution

# ═══════════════════════════════════════════════════════════════
#  GABA-A binding kinetics weights
#  [CAL] Bind propensity = k_on * (w_rest * ligand_rest + w_active * ligand_active * drive)
#  w_rest + w_active = 1.0
#  Ref: Chang et al. 1996, doi:10.1016/S0006-3495(96)79393-2
# ═══════════════════════════════════════════════════════════════

BIND_RESTING_WEIGHT: float = 0.35  # [CAL] Resting-state ligand contribution
BIND_ACTIVE_WEIGHT: float = 0.65  # [CAL] Active-state ligand contribution

# ═══════════════════════════════════════════════════════════════
#  Desensitization kinetics
#  [LIT] Desensitization rate depends on activity:
#  des_propensity = des_rate * (base + drive_fraction * activity_drive)
#  Ref: Jones & Bhatt 1998, doi:10.1523/JNEUROSCI.18-09-03392.1998
# ═══════════════════════════════════════════════════════════════

DESENSITIZATION_BASELINE_FRACTION: float = 0.40  # [LIT] Base desensitization rate
DESENSITIZATION_DRIVE_FRACTION: float = 0.60  # [LIT] Activity-dependent fraction

# ═══════════════════════════════════════════════════════════════
#  Recovery kinetics
#  [LIT] Recovery from desensitization is inhibited by activity:
#  rec_propensity = rec_rate * (1.0 - dampening * activity_drive)
#  Ref: Jones & Bhatt 1998
# ═══════════════════════════════════════════════════════════════

RECOVERY_ACTIVITY_DAMPENING: float = 0.50  # [LIT] Activity inhibits recovery

# ═══════════════════════════════════════════════════════════════
#  Default rate constants (fallbacks when config absent)
#  [LIT] Typical GABA-A kinetics
#  Ref: Barberis et al. 2007, doi:10.1113/jphysiol.2007.139899
# ═══════════════════════════════════════════════════════════════

DEFAULT_K_ON_HZ: float = 0.18  # [LIT] Binding rate
DEFAULT_K_OFF_HZ: float = 0.06  # [LIT] Unbinding rate
DEFAULT_DES_RATE_HZ: float = 0.02  # [LIT] Desensitization rate fallback
DEFAULT_REC_RATE_HZ: float = 0.02  # [LIT] Recovery rate fallback

# ═══════════════════════════════════════════════════════════════
#  Plasticity drive scaling
#  [CAL] How activator deviation maps to plasticity drive.
# ═══════════════════════════════════════════════════════════════

PLASTICITY_DRIVE_SCALE: float = 2.0  # [CAL] Scale factor for |activator - mean|
