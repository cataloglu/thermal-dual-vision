# Visual Assets for Smart Motion Detector Add-on

This document describes the visual assets required for the Home Assistant Add-on presentation.

## Required Assets

### icon.png
**Required Dimensions:** 128x128 pixels
**Format:** PNG with transparency support
**Purpose:** Displayed in the Home Assistant Add-on store and sidebar
**Location:** Root directory of the add-on (`./icon.png`)

**Design Guidelines:**
- Use a square aspect ratio
- Ensure the icon is clearly visible at small sizes (48x48 preview)
- Use colors that work well on both light and dark backgrounds
- Prefer simple, recognizable symbols over complex designs
- Consider using the motion sensor theme (waves, radar, detection symbols)
- PNG format with alpha channel for transparency

**Recommended Design Elements:**
- Motion detection symbol (concentric circles, radar waves)
- Camera or surveillance icon
- AI/Smart technology indicators
- Color scheme: Blue/cyan for technology, orange/red for alerts

### logo.png
**Required Dimensions:** 256x256 pixels
**Format:** PNG with transparency support
**Purpose:** Displayed in the Add-on details page and documentation
**Location:** Root directory of the add-on (`./logo.png`)

**Design Guidelines:**
- Larger, more detailed version of the icon design
- Should maintain consistent branding with icon.png
- Can include more detail since it's displayed at larger sizes
- Use transparency for non-square designs
- Ensure good visibility on both light and dark backgrounds

**Recommended Design Elements:**
- Same core design as icon.png but with more detail
- Can include subtle gradients or shadows
- May include product name or tagline if legible
- Consider adding visual elements like motion trails or AI network patterns

## Design Specifications

### Color Palette Suggestions
- **Primary:** #2196F3 (Blue - Technology/Reliability)
- **Secondary:** #FF9800 (Orange - Alert/Motion)
- **Accent:** #4CAF50 (Green - Active/Success)
- **Dark:** #263238 (Dark backgrounds)
- **Light:** #ECEFF1 (Light backgrounds)

### File Requirements
- **Format:** PNG (Portable Network Graphics)
- **Color Mode:** RGB with Alpha channel
- **Bit Depth:** 24-bit color + 8-bit alpha (32-bit total)
- **Compression:** PNG compression (lossless)
- **Background:** Transparent (alpha channel)

## Creating the Assets

### Design Tools
You can use any of the following tools to create the assets:

**Professional:**
- Adobe Illustrator / Photoshop
- Affinity Designer / Photo
- Sketch (macOS)

**Free/Open Source:**
- GIMP (https://www.gimp.org/)
- Inkscape (https://inkscape.org/)
- Figma (https://www.figma.com/)
- Canva (https://www.canva.com/)

**AI-Assisted:**
- DALL-E / Midjourney (generate base designs)
- Stable Diffusion (local generation)

### Quick Start Template

If you need to create placeholder assets quickly:

```bash
# Using ImageMagick (if installed)
# Create a simple icon.png
convert -size 128x128 xc:transparent \
  -fill '#2196F3' -draw 'circle 64,64 64,20' \
  -fill '#FF9800' -draw 'circle 64,64 64,32' \
  -fill '#4CAF50' -draw 'circle 64,64 64,44' \
  icon.png

# Create a simple logo.png
convert -size 256x256 xc:transparent \
  -fill '#2196F3' -draw 'circle 128,128 128,40' \
  -fill '#FF9800' -draw 'circle 128,128 128,64' \
  -fill '#4CAF50' -draw 'circle 128,128 128,88' \
  logo.png
```

### Manual Creation Steps

1. **Create a new image** with the required dimensions (128x128 or 256x256)
2. **Set transparent background**
3. **Design your icon/logo** following the guidelines above
4. **Export as PNG** with transparency
5. **Verify dimensions** using:
   ```bash
   file icon.png logo.png
   ```
6. **Place files** in the root directory of the add-on

## Validation

Before finalizing your assets, verify:

- [ ] `icon.png` is exactly 128x128 pixels
- [ ] `logo.png` is exactly 256x256 pixels
- [ ] Both files are PNG format with transparency
- [ ] Icons are visible on both light and dark backgrounds
- [ ] Design is consistent between icon and logo
- [ ] Files are optimized (compressed but not lossy)
- [ ] Files are placed in the add-on root directory

### Validation Commands

```bash
# Check file dimensions
identify icon.png logo.png

# Check file size (should be reasonable, < 50KB each)
ls -lh icon.png logo.png

# Verify PNG format
file icon.png logo.png
```

## Usage in Home Assistant

### Where Assets Appear

**icon.png:**
- Add-on Store tile
- Add-on list in Supervisor
- Sidebar navigation (if panel_icon not set)
- Add-on info page header

**logo.png:**
- Add-on details page
- Add-on store featured section
- Documentation pages
- Social media previews

### Testing Your Assets

1. Place `icon.png` and `logo.png` in the add-on root directory
2. Rebuild the add-on in Home Assistant
3. Navigate to **Supervisor → Add-on Store**
4. Verify your icon appears correctly
5. Open the add-on details page
6. Verify your logo appears correctly
7. Test in both light and dark themes

## Resources

### Home Assistant Guidelines
- [Home Assistant Add-on Documentation](https://developers.home-assistant.io/docs/add-ons)
- [Add-on Branding Guidelines](https://developers.home-assistant.io/docs/add-ons/presentation)

### Design Inspiration
- Material Design Icons: https://materialdesignicons.com/
- Font Awesome: https://fontawesome.com/
- Home Assistant Icons: https://www.home-assistant.io/docs/configuration/customizing-devices/

### Icon Optimization
- TinyPNG: https://tinypng.com/ (reduce file size)
- ImageOptim: https://imageoptim.com/ (macOS)
- Squoosh: https://squoosh.app/ (web-based)

## Notes

- These assets are **optional but highly recommended** for a professional appearance
- If assets are not provided, Home Assistant will use default placeholder icons
- The add-on will function correctly without custom assets
- Assets should be created by the end user or a designer
- Consider your add-on's purpose when designing (motion detection, surveillance, AI)

## TODO

- [ ] Create or commission `icon.png` (128x128)
- [ ] Create or commission `logo.png` (256x256)
- [ ] Test assets in Home Assistant (both light and dark themes)
- [ ] Optimize file sizes if needed
- [ ] Consider creating additional sizes for future use (512x512, 1024x1024)
