"""Audio loading, feature extraction, and frontend resource generation."""

from __future__ import annotations

import json
import math
import warnings
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from scipy.io import wavfile
from scipy.io.wavfile import WavFileWarning
from scipy.signal import get_window


@dataclass(frozen=True)
class AudioData:
    samples: np.ndarray
    sample_rate: int
    channel_count: int
    duration_sec: float


@dataclass(frozen=True)
class FeatureVector:
    names: tuple[str, ...]
    values: np.ndarray

    def as_dict(self) -> dict[str, float]:
        return {name: float(value) for name, value in zip(self.names, self.values)}


def load_audio(path: str | Path) -> AudioData:
    """Read a wav file as normalized mono float32 samples."""

    wav_path = Path(path)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", WavFileWarning)
        sample_rate, raw = wavfile.read(wav_path)
    raw_array = np.asarray(raw)
    if raw_array.size == 0:
        raise ValueError(f"Audio file is empty: {wav_path}")

    channel_count = 1 if raw_array.ndim == 1 else raw_array.shape[1]
    if np.issubdtype(raw_array.dtype, np.integer):
        max_value = float(np.iinfo(raw_array.dtype).max)
        samples = raw_array.astype(np.float32) / max_value
    else:
        samples = raw_array.astype(np.float32)

    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    samples = np.nan_to_num(samples, copy=False)
    duration_sec = float(len(samples) / sample_rate) if sample_rate else 0.0
    return AudioData(samples=samples, sample_rate=int(sample_rate), channel_count=channel_count, duration_sec=duration_sec)


def extract_feature_vector(audio: AudioData) -> FeatureVector:
    """Extract compact deterministic time/frequency features for the demo classifier."""

    samples = audio.samples.astype(np.float64, copy=False)
    if samples.size == 0:
        raise ValueError("Cannot extract features from an empty signal")

    centered = samples - float(np.mean(samples))
    abs_signal = np.abs(centered)
    rms = float(np.sqrt(np.mean(centered**2)))
    peak = float(np.max(abs_signal))
    zcr = float(np.mean(np.diff(np.signbit(centered)) != 0)) if centered.size > 1 else 0.0

    window = get_window("hann", centered.size, fftbins=True)
    spectrum = np.abs(np.fft.rfft(centered * window))
    power = spectrum**2
    freqs = np.fft.rfftfreq(centered.size, d=1.0 / audio.sample_rate)
    total_power = float(np.sum(power)) + 1e-12
    probabilities = power / total_power

    centroid = float(np.sum(freqs * probabilities))
    bandwidth = float(np.sqrt(np.sum(((freqs - centroid) ** 2) * probabilities)))
    cumulative = np.cumsum(power)
    rolloff_idx = int(np.searchsorted(cumulative, 0.85 * cumulative[-1])) if cumulative.size else 0
    rolloff = float(freqs[min(rolloff_idx, len(freqs) - 1)]) if freqs.size else 0.0
    dominant = float(freqs[int(np.argmax(power))]) if power.size else 0.0
    flatness = float(math.exp(np.mean(np.log(power + 1e-12))) / (np.mean(power) + 1e-12))

    nyquist = audio.sample_rate / 2.0
    band_edges = np.linspace(0.0, nyquist, 9)
    band_features: list[float] = []
    for start, end in zip(band_edges[:-1], band_edges[1:]):
        mask = (freqs >= start) & (freqs < end)
        band_features.append(float(np.sum(power[mask]) / total_power))

    percentile_values = np.percentile(centered, [5, 25, 50, 75, 95])
    names = (
        "duration_sec",
        "sample_rate",
        "channel_count",
        "mean",
        "std",
        "rms",
        "peak",
        "crest_factor",
        "zero_crossing_rate",
        "abs_mean",
        "p05",
        "p25",
        "p50",
        "p75",
        "p95",
        "spectral_centroid",
        "spectral_bandwidth",
        "spectral_rolloff_85",
        "spectral_flatness",
        "dominant_frequency",
        "band_energy_1",
        "band_energy_2",
        "band_energy_3",
        "band_energy_4",
        "band_energy_5",
        "band_energy_6",
        "band_energy_7",
        "band_energy_8",
    )
    values = np.asarray(
        [
            audio.duration_sec,
            audio.sample_rate,
            audio.channel_count,
            float(np.mean(centered)),
            float(np.std(centered)),
            rms,
            peak,
            peak / (rms + 1e-12),
            zcr,
            float(np.mean(abs_signal)),
            *[float(v) for v in percentile_values],
            centroid,
            bandwidth,
            rolloff,
            flatness,
            dominant,
            *band_features,
        ],
        dtype=np.float64,
    )
    return FeatureVector(names=names, values=np.nan_to_num(values))


def create_feature_resources(
    audio: AudioData,
    feature: FeatureVector,
    sample_uid: str,
    source_path: str | Path,
    output_dir: str | Path,
) -> dict[str, str]:
    """Write waveform PNG, spectrum PNG, and feature JSON resources."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    safe_uid = _safe_filename(sample_uid)
    waveform_path = out / f"{safe_uid}_waveform.png"
    spectrum_path = out / f"{safe_uid}_spectrum.png"
    feature_path = out / f"{safe_uid}_features.json"

    _plot_waveform(audio, waveform_path)
    _plot_spectrum(audio, spectrum_path)
    payload = {
        "sample_uid": sample_uid,
        "source_path": str(source_path),
        "sample_rate": audio.sample_rate,
        "channel_count": audio.channel_count,
        "duration_sec": audio.duration_sec,
        "features": feature.as_dict(),
    }
    feature_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "waveform_uri": str(waveform_path),
        "spectrum_uri": str(spectrum_path),
        "feature_uri": str(feature_path),
    }


def _plot_waveform(audio: AudioData, path: Path) -> None:
    time_axis = np.arange(audio.samples.size) / audio.sample_rate
    fig, ax = plt.subplots(figsize=(9, 3), dpi=140)
    ax.plot(time_axis, audio.samples, color="#2563eb", linewidth=0.8)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _plot_spectrum(audio: AudioData, path: Path) -> None:
    centered = audio.samples - float(np.mean(audio.samples))
    spectrum = np.abs(np.fft.rfft(centered * get_window("hann", centered.size, fftbins=True)))
    freqs = np.fft.rfftfreq(centered.size, d=1.0 / audio.sample_rate)
    db = 20.0 * np.log10(spectrum + 1e-8)
    fig, ax = plt.subplots(figsize=(9, 3), dpi=140)
    ax.plot(freqs, db, color="#0f766e", linewidth=0.8)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Magnitude (dB)")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _safe_filename(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value)
