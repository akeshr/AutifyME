# Test Images Directory

Place product images here for local testing.

## Recommended Images

- **sneaker.jpg** - Canvas sneakers (for cataloging scenarios)
- **tshirt.jpg** - T-shirt product shot
- **dress.jpg** - Dress or formal wear
- **product.jpg** - Generic product (for ambiguous testing)
- **batch/** - Directory with multiple products for batch cataloging

## Supported Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)
- WebP (.webp)
- GIF (.gif)

## Usage

```bash
# Test with single image
uv run python -m autifyme_agents.cli.pm_chat "Catalog this" --media test_images/sneaker.jpg

# Interactive mode
uv run python -m autifyme_agents.cli.pm_chat --interactive
# > media test_images/product.jpg
# > Catalog this product, price $49.99
```
