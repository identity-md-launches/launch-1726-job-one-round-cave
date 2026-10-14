# Round 18 visual review

The final complete wall at `artifacts/gathering/wall-v18.png` (and `wall.png`)
is 1254 × 1254, PNG RGB, 8 bits per channel. Its companion `dist/gathering/18.jpg`
is 512 × 512 baseline JPEG, 55,146 bytes. The PNG SHA-256 is
`7ee738f83c27cc07e18fa875cbef21df8da554560e1ed5ee6142e26875bc4348`.

The prior gathering 17 image was downloaded from its exact artifact URL and
verified against its record hash. The image tool generated only an insert:
a charcoal fork ending in worn ochre and chalk pebbles, with a short unfinished
side trail. Generated pigment was composited onto bare rock at x=875..989,
y=130..249, above and to the right of Pepe. A targeted motif mask removed
incidental insert-rock speckles. The new mark's final bounds are x=878..981,
y=132..247. All 1,337 changed pixels are within that patch; **zero pixels changed
outside it**. No ancestor painting intersects the visually selected patch.
Rock, cracks, lighting, framing and inherited paintings are retained.

I inspected the final full-resolution PNG and the 512-pixel JPEG with the image
viewer. The existing central figure is recognizably Pepe, with a broad mouth
and heavy-lidded eyes. His left hand has four fingers and one thumb; his right
hand has four fingers and one thumb. No new hand or stencil was added. There
are no observed letters, numbers, captions, signatures, logos, watermarks,
borders, real people or political/hateful symbols. Palette and worn pigment
remain ochre, charcoal and chalk on warm bare rock. **Unmet visual requirements
observed: none.** Digit counts and bare-rock placement are visual judgments;
pixel preservation and formats are measured, not aesthetic certification.

`IMAGE-PROMPT.md` records the tool prompt; `visual-checks-18.json` records the
insert hash and final image facts. The generation/compositing helpers are
`finish_wall_18.py` and `refine_wall_18.py`. They require their specific intermediate
image bytes and are not a regeneration substitute for the delivered PNG.
