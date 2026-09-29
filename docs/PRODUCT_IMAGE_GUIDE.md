# Product image guide

## Pixel-preserving product key visuals

The `product-kv` and `batch` workflows generate an empty scene/background and composite the supplied product PNG afterward. The generated model never redraws the product label. Opaque product pixels are carried from the input image; the alpha edge is used as the compositing mask.

1. Put the product cutout PNG in `assets/products/`.
2. It must have transparent pixels around the product. The runner checks alpha before submitting.
3. If the PNG is smaller than the selected canvas, the runner centers it on a transparent canvas without resizing the product. If the PNG already matches the selected size, its placement is used as-is.
4. For a deliberately off-center layout or more negative space, prepare a full-size transparent canvas and position the product before upload. The runner does not resize oversized product artwork.
5. Prompt for the empty scene, lighting, surface, materials, and surrounding set. For example: `empty premium apothecary studio, pale limestone surface, soft professional side lighting, generous negative space, no bottle, no packaging, no text`.

Because the product is composited after background generation, the generated scene does not automatically create a correct contact shadow or reflections on the product. Include a natural shadow in the source cutout when possible, or add a separately reviewed shadow layer during final retouching. Avoid asking the model to recreate packaging or brand text.

## When using inpaint or img2img

These workflows regenerate pixels through a diffusion model and do not guarantee exact product typography or color. Use the pixel-preserving composite path for brand-critical packaging. Inpaint aims to change only the white mask region, but VAE encoding/decoding and soft mask edges can alter nearby pixels; it is not a bitwise preservation guarantee.

## Mask convention

For the inpaint workflow, prepare a mask the same pixel dimensions as the source image. White pixels are regenerated; black pixels are retained. Gray pixels create a soft transition. The workflow uses the red channel of the mask PNG.
