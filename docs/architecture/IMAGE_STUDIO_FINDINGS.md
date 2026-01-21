# Image Studio Tool - Testing Findings & Fixes

**Date:** 2026-01-21
**Status:** Testing Complete, Analysis In Progress

---

## Executive Summary

Comprehensive testing of image_studio tool across different image types, materials, and scenarios. The tool performs excellently in most cases but has a specific issue with **tinted transparent materials** (colored PET bottles).

---

## Test Results Summary

| Test | Image | Scenario | Result | Notes |
|------|-------|----------|--------|-------|
| 1 | ArrowBottles | Hero (blue) | PARTIAL | Transparency too saturated |
| 2 | ArrowBottles | Lifestyle | PARTIAL | Same transparency issue |
| 3 | PET_CAN_JAR | Hero | EXCELLENT | Perfect transformation from messy phone photo |
| 4 | PET_CAN_JAR | Transparent BG | EXCELLENT | Clean PNG cutout with alpha |
| 5 | PAVISHA Lid | Opaque matte | EXCELLENT | Embossed texture visible, correct material |
| 6 | StackedJarImage | Decorated jars | GOOD | Artwork preserved |

---

## Key Findings

### Finding 1: Tinted Transparent Materials - ISSUE

**Problem:** Transparent tinted PET bottles (like Arrow H2O) render with too much color saturation, looking more opaque than see-through.

**Evidence:**
- Source Arrow bottles are ~80-85% transparent with visible color tint
- Generated images show saturated opaque color instead of see-through tinted plastic
- Multiple prompt attempts show model bias toward solid colors
- Crystal-clear attempt went too far (too washed out)

**Root Cause Analysis:**
1. Gemini 3 Pro Image has a "beautification" bias toward saturated colors
2. The balance between "visible color" and "see-through" is hard to convey
3. Generic transparency % instructions don't translate well
4. Model interprets "blue tinted" as "make it blue" rather than "tint what you see through"

**Proposed Fix:** Added new section to system prompt:
```
=== TRANSPARENT TINTED MATERIALS (CRITICAL) ===
- Background MUST be visible through the material
- Color is a TINT, not opacity
- Like tinted sunglasses - see through with color cast
```

**Status:** Fix applied, marginal improvement. May need creative specialist to provide more explicit specs.

---

### Finding 2: Clear Transparent Materials - EXCELLENT

**Observation:** When materials are described as "crystal clear" (no tint), the tool renders transparency perfectly.

**Evidence:** PET_CAN_JAR with clear body rendered with excellent see-through quality.

**Conclusion:** The issue is specifically with TINTED transparency, not transparency in general.

---

### Finding 3: Messy Phone Photo Transformation - EXCELLENT

**Observation:** The tool excels at transforming messy phone photos (bad lighting, cluttered backgrounds, hands in frame) into professional product photography.

**Evidence:** PET_CAN_JAR transformed from car interior shot with hand holding jar into professional studio-quality image.

**No fix needed** - this is working as intended.

---

### Finding 4: Opaque Matte Materials - EXCELLENT

**Observation:** Opaque matte plastics with embossed textures render very well.

**Evidence:** PAVISHA lid with embossed PAVISHA text and floral pattern visible through subtle lighting.

**No fix needed** - this is working as intended.

---

### Finding 5: Transparent Background (PNG) - EXCELLENT

**Observation:** PNG cutouts with alpha channel transparency work perfectly.

**Evidence:** PET_CAN_JAR PNG cutout with clean edges, no halos, proper alpha channel.

**No fix needed** - this is working as intended.

---

### Finding 6: CGI vs Photography Aesthetic - RESOLVED

**Problem (original):** Hero shots looked "rendered/CGI" instead of "photographed."

**Fix Applied:** Updated TOOL_SYSTEM_PROMPT with:
- "PROFESSIONAL PHOTOGRAPHY, NOT CGI" core principle
- Photographic authenticity section
- Explicit pitfalls about CGI aesthetic
- Gradient backgrounds instead of flat white

**Result:** Hero shots now look more like professional studio photography.

---

## System Prompt Changes Made

### Change 1: Photography Framing
**Location:** Opening of TOOL_SYSTEM_PROMPT
**Change:** Reframed from "retoucher" to "master product photographer with 20 years experience"

### Change 2: Core Principle
**Location:** After labeled images section
**Change:** Added "PROFESSIONAL PHOTOGRAPHY, NOT CGI" with explicit anti-goal

### Change 3: Photographic Authenticity Section
**Location:** After AVOID section
**Change:** Added detailed guidance on what makes photos look real (highlights, texture, shadows)

### Change 4: Transparent Tinted Materials Section
**Location:** Before SPEC REFERENCE
**Change:** Added explicit guidance for tinted transparent plastics

### Change 5: Updated Pitfalls
**Location:** PITFALLS TO AVOID section
**Change:** Added:
- FLAT WHITE BACKGROUNDS
- OVER-SMOOTH SURFACES
- CGI/RENDER AESTHETIC

---

## Remaining Issues

### Issue 1: Tinted Transparency Balance
**Status:** RESOLVED

**Breakthrough Discovery:** The key to rendering tinted transparent materials correctly is emphasizing CLARITY over COLOR.

| Version | Prompting Approach | Result |
|---------|-------------------|--------|
| V1 | "tinted blue", "blue PET" | Too saturated, opaque-looking |
| V2 | "like tinted sunglasses" analogy | Better, more transparent |
| V3 | "CRYSTAL CLEAR with very subtle tint" | **EXCELLENT - true transparency** |

**The Winning Pattern:**
- `primary_material`: "CRYSTAL CLEAR [material] with very subtle [color] tint"
- `rendering_notes`: "It is NOT a [color] [product] - it is a clear [product] with minimal [color] tinting"
- `fidelity.preserve_colors`: "VERY SUBTLE [color] tint - almost clear with just a hint of [color]"
- Explicit prohibitions: "No opacity. No solid color."

**Root Cause:** Gemini interprets "blue bottle" or "tinted blue" as instructions to make something blue, not as a description of subtle tinting. Counter-instruction ("It is NOT a blue bottle") overrides this bias.

---

## Recommendations for Creative Specialist

Based on tool testing, the creative specialist should:

1. **For tinted transparent products:**
   - Explicitly describe what should be visible THROUGH the material
   - Use "tinted sunglasses" analogy in specs
   - Specify that background must be visible through body
   - Avoid high saturation color descriptions

2. **For all products:**
   - Always specify gradient backgrounds for hero shots (not flat white)
   - Include contact shadow specs for grounding
   - Emphasize "professional studio photography" aesthetic

3. **Protocol updates needed:**
   - Review image_studio.protocol for transparency handling
   - Add guidance on tinted vs clear transparent materials
   - Include quality checkpoints for transparency rendering

---

## Protocol Changes Made

### catalog_visual.protocol (domain=visual)

1. **Added TINTED vs CLEAR Transparency section** - Critical distinction table explaining:
   - CLEAR: Background visible directly through, no color cast
   - TINTED: Background visible THROUGH with COLOR CAST (like tinted sunglasses)

2. **Added Anti-Simulation Principle** - Explicit guidance on what makes renders look CGI vs photographic:
   - Wavy internal distortion (fake refraction waves)
   - Vertical light streaks (artificial form highlights)
   - Exaggerated base darkening (dark ring artifacts)
   - Artificial rim highlights (CGI edge glow)

3. **Added TransparencyProfile Examples** - Concrete examples for:
   - Crystal Clear PET Bottle with Honey (92% clarity)
   - Frosted Glass Jar Empty (35% clarity, 70% frost)
   - Amber PET Medicine Bottle (75% clarity, amber tint)

4. **Added Transparent Material Syntax Pattern** - Complete checklist and example code

5. **Updated example code** - Uses gradient background instead of solid white

### image_studio.protocol (tool mastery)

1. **Updated Pattern 5 (Hero Shot)** - Changed from `solid_color: white` to `gradient: white to light gray`

2. **Added Pattern 5b** - Specific pattern for TINTED transparent materials with:
   - Full rendering_notes template with anti-artifact language
   - Complete transparency profile example
   - Critical rules (background visible THROUGH, color as TINT not fill)

3. **Updated Pattern 2** - Added gradient as recommended option, solid white only for platform requirements

4. **Added explicit rendering_notes guidance** - Required phrases for transparent materials:
   - "can see THROUGH to background"
   - "natural refraction only"
   - "no artificial rim highlights"
   - "no internal distortion patterns"
   - "photograph-like simplicity"

5. **Added new anti-patterns**:
   - Saturated color for TINTED materials -> Use "THROUGH transparent body" language
   - Solid white background for hero -> Use gradient
   - Missing anti-artifact language -> Include "no artificial rim highlights"

---

## Next Steps

1. [x] Complete tool testing
2. [x] Document findings
3. [x] Analyze creative specialist prompt
4. [x] Analyze creative specialist protocols
5. [x] Implement protocol improvements
6. [x] Re-test with updated protocols to verify fix
7. [x] Document breakthrough "Clarity-Over-Color" pattern

## Conclusion

**All major issues resolved.** The image_studio tool now has:

1. **Photography-first prompting** - Outputs look like real studio photos, not CGI
2. **Gradient backgrounds** - Professional depth instead of flat white
3. **Tinted transparency breakthrough** - "Clarity-Over-Color" pattern produces true see-through materials
4. **Anti-artifact language** - Prevents rim highlights, distortion patterns, streaks
5. **Comprehensive protocols** - Both catalog_visual and image_studio updated with patterns

The creative specialist can now produce professional-quality outputs for all material types tested.
