"""Hand-picked non-TTS selections (after reviewing spectrograms / onsets / loop metrics) -> qa/panic_selection_extra.json."""
import json, os
AUD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = lambda d, f: os.path.join(AUD, "gen", d, f + ".flac")  # noqa: E731
SA3 = "Stable Audio 3 Medium (ComfyUI)"
E = []


def fx(name, cat, src, desc, gen=SA3, **kw):
    E.append(dict(name=name, category=cat, source=src, description=desc, generator=gen, **kw))


# ---------------------------------------------------------------- piano (3D, mono)
fx("SFX_Piano_Crash_01", "piano", G("piano_crash_low", "piano_crash_low_s811_1"),
   "Grand piano slammed with both forearms on the low keys: dissonant bass cluster, ~1 s held, long ringing decay.", mom=-12.0, keep=4.0, fade_out=0.5)
fx("SFX_Piano_Crash_02", "piano", G("piano_crash_mid", "piano_crash_mid_s812_1"),
   "Grand piano banged with both fists in the middle register: harsh mid cluster, then ringing decay.", mom=-12.0, keep=3.8, fade_out=0.5)
fx("SFX_Piano_Crash_03", "piano", G("piano_crash_doublecomp", "piano_crash_doublecomp_c1_0"),
   "Two quick fist slams 0.3 s apart (low-mid cluster then mid cluster), then ringing decay.",
   gen=SA3 + ": two generated slams layered 0.30 s apart (no single take had two distinct hits)", mom=-12.0, keep=3.6, fade_out=0.5)
# ---------------------------------------------------------------- event SFX
fx("SFX_Explosion_01", "sfx", G("sfx_explosion", "sfx_explosion_s821_1"), "Explosion in the ballroom: deep boom, glass and debris.",
   mom=-10.0, keep=5.0, fade_out=0.8)
fx("SFX_Explosion_02", "sfx", G("sfx_explosion", "sfx_explosion_s821_0"), "Explosion, variant: sharper blast, falling debris.",
   mom=-10.0, keep=5.0, fade_out=0.8)
fx("SFX_Fire_Whoosh_01", "sfx", G("sfx_fire_whoosh", "sfx_fire_whoosh_s822_1"), "Fire ignites: rising whoosh and roar (one-shot).",
   mom=-12.0, keep=2.2, fade_out=0.4)
fx("SFX_Fire_Crackle_Loop", "sfx", G("sfx_fire_crackle", "sfx_fire_crackle_s823_1"), "Large fire burning: crackling wood and flames, seamless loop.",
   kind="loop", lufs=-24.0)
fx("SFX_Power_Down_01", "sfx", G("sfx_power_down", "sfx_power_down_s824_1"), "Power cut: heavy switch clunk, electric hum winding down.",
   mom=-12.0, keep=2.6, fade_out=0.4, mono=False)
for k, t in enumerate((2.22, 3.22, 5.28, 7.32)):
    fx(f"SFX_Robot_Step_{k + 1:02d}", "sfx", G("sfx_robot_steps", "sfx_robot_steps_s826_1"),
       f"Heavy metallic robot footstep (single step cut at {t:.2f} s of a generated walk).", cut=[t - 0.06, t + 0.8], mom=-15.0, fade_out=0.15)
fx("SFX_Robot_Servo_01", "sfx", G("sfx_servo", "sfx_servo_s827_0"), "Robot servo whirr: electric motor whine with gears, ~1 s.",
   mom=-16.0, keep=1.2, fade_out=0.15)
fx("SFX_Laser_Zap_01", "sfx", G("sfx_laser", "sfx_laser_s828_0"), "Retro ray-gun zap, descending chirp with a short tail.",
   mom=-13.0, keep=0.9, fade_out=0.2)
fx("SFX_Laser_Zap_02", "sfx", G("sfx_laser", "sfx_laser_s828_3"), "Retro ray-gun zap, sharper and brighter.", mom=-13.0, keep=0.6, fade_out=0.08)
fx("SFX_Laser_Zap_03", "sfx", G("sfx_laser2", "sfx_laser2_s836_1"), "Retro ray-gun zap, clean descending chirp.", mom=-13.0, keep=0.9,
   fade_out=0.2)
fx("SFX_Power_Up_01", "sfx", G("sfx_power_up2", "sfx_power_up2_s835_2"), "Power returns: switch clunk, rising electric whine and buzzing hum.",
   mom=-14.0, keep=2.2, fade_out=0.5, mono=False)
fx("SFX_Event_Alarm_01", "sfx", G("sfx_alarm_sting", "sfx_alarm_sting_s829_0"), "Event alarm sting: dissonant brass stab with timpani, ~2.5 s.",
   lufs=-15.0, keep=3.0, fade_out=0.5, mono=False)
# ---------------------------------------------------------------- screams / cries (non-verbal, mono, Stable Audio 3: the Qwen3-TTS
# "Aaaah !" takes are clean sung vowels without the noisy roughness of a real scream, the SA3 takes have it)
SCREAMS = [
    ("f", "panic_sa_scream_f", "panic_sa_scream_f_s801_1", "scream", "adult woman, piercing scream of terror"),
    ("m", "panic_sa_scream_m", "panic_sa_scream_m_s802_0", "scream", "adult man, panicked scream"),
    ("f", "panic_sa_scream_f", "panic_sa_scream_f_s801_3", "scream", "adult woman, short shriek"),
    ("m", "panic_sa_scream_m", "panic_sa_scream_m_s802_2", "scream", "adult man, long terrified yell"),
    ("f", "panic_sa_scream_of", "panic_sa_scream_of_s806_1", "scream", "older woman, shrill shriek"),
    ("m", "panic_sa_scream_om", "panic_sa_scream_om_s807_1", "scream", "older man, hoarse bellow of fear"),
    ("f", "panic_sa_scream_f", "panic_sa_scream_f_s801_2", "scream", "adult woman, lower scream"),
    ("m", "panic_sa_scream_m", "panic_sa_scream_m_s802_3", "scream", "adult man, short scream"),
    ("f", "panic_sa_gasp_f", "panic_sa_gasp_f_s803_0", "cry", "woman, short frightened cry 'ah!'"),
    ("m", "panic_sa_cry_m", "panic_sa_cry_m_s804_1", "cry", "man, short shocked shout 'ah!'"),
    ("f", "panic_sa_gasp2_f", "panic_sa_gasp2_f_s805_1", "gasp", "woman, sharp horrified gasp with a small cry"),
    ("m", "panic_sa_cry_m", "panic_sa_cry_m_s804_3", "cry", "man, sharp frightened cry"),
]
for k, (g, d, f, kind, desc) in enumerate(SCREAMS):
    E.append(dict(name=f"VO_Panic_Scream_{k + 1:02d}_{g}", category="scream", gender=g, source=G(d, f), voice_id=f"sa3_{kind}_{g}",
                  voice_label=desc, voice_description="Generic voice generated by Stable Audio 3 from a text prompt (no guest voice clone).",
                  register=kind, text="", whispered=False, nonverbal=True, generator=SA3 + " (text-to-audio)"))
# ---------------------------------------------------------------- event music (stereo loops)
for name, d, f, desc in [
    ("MUS_Event_Attack", "mus_ev_attack", "mus_ev_attack_s831_1", "Attack / chaos: frantic 1930s film-noir action, stabbing brass, racing strings, timpani."),
    ("MUS_Event_Fire", "mus_ev_fire", "mus_ev_fire_s832_1", "Fire: urgent 1930s orchestral, swirling string runs, alarm brass calls."),
    ("MUS_Event_Blackout", "mus_ev_blackout", "mus_ev_blackout_s833_1", "Blackout / suspense: slow pizzicato bass, eerie tremolo strings, celesta."),
    ("MUS_Event_Robot", "mus_ev_robot", "mus_ev_robot_s834_0", "Robot / menace: mechanical 1930s sci-fi march, low brass ostinato, theremin."),
]:
    fx(name, "music", G(d, f), desc, kind="music", lufs=-16.0, min_len=30, max_len=60, mono=False)
json.dump(E, open(os.path.join(AUD, "qa", "panic_selection_extra.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(len(E))
