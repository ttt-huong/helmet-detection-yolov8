# Independent pixel adjudication: 13-frame sample

## Scope and method

I visually reviewed the 13 original images extracted from the locked pilot ZIP, using the full frames and enlarged crops of small or blurred heads. I checked the sample filenames, dimensions, and SHA-256 values against the pilot roster; all 13 matched. The sample-selection report supplied the filenames and hashes, and I did see its written A/B observations while opening it. This pass is therefore not blind. I did not open either reviewer JSON or upstream annotations, and I derived the findings and approximate boxes below from the original pixels rather than accepting those observations as labels.

Boxes are approximate normalized `xywh` over the full original image; pixel `xywh` estimates are included to make the bounds reviewable. They should be treated as visual proposals, not pixel-perfect labels. The box covers the visible head and worn headwear, not the body. `hard_hat_worn` is review class 0, `cap_worn` class 2, and `bare_head` class 4 per the rubric. An `uncertain` item has no settled class. All 13 frames show photographic real scenes; I saw no people in posters, printed photos, or screens and no depiction surface to box.

## Frame findings

### `source-c285b53fb701de95fbfe70714765e8c7.jpg` — 1536×1024

Four localized heads: three workers wear hard hats and the nearer lower-left worker has visible tied-back hair with no hat. The middle hard hat is white; upper-left and upper-right hats are light/yellow and white respectively.

- Confirmed `hard_hat_worn`: upper-left, xywh≈`(0.2669, 0.2148, 0.0521, 0.0977)`; px≈`(410,220,80,100)`.
- Confirmed `hard_hat_worn`: center, xywh≈`(0.5208, 0.3076, 0.0553, 0.1025)`; px≈`(800,315,85,105)`.
- Confirmed `hard_hat_worn`: upper-right, xywh≈`(0.7487, 0.2197, 0.0488, 0.1025)`; px≈`(1150,225,75,105)`.
- Confirmed `bare_head`: foreground-left, xywh≈`(0.2572, 0.4590, 0.0423, 0.0928)`; px≈`(395,470,65,95)`.

### `source-cdc3f2865204a12157c3f233e5f9bfaf.jpg` — 2048×1360

Four workers are grouped at the right side: three wear white hard hats; the nearer center-right worker has uncovered short hair. The distinction is visible in the original at full frame.

- Confirmed `hard_hat_worn`: near-left worker, xywh≈`(0.5420, 0.3824, 0.0659, 0.1066)`; px≈`(1110,520,135,145)`.
- Confirmed `hard_hat_worn`: rear-center worker, xywh≈`(0.6519, 0.3309, 0.0610, 0.1066)`; px≈`(1335,450,125,145)`.
- Confirmed `bare_head`: center-front worker, xywh≈`(0.6860, 0.4007, 0.0610, 0.1103)`; px≈`(1405,545,125,150)`.
- Confirmed `hard_hat_worn`: right worker, xywh≈`(0.7446, 0.3272, 0.0586, 0.1066)`; px≈`(1525,445,120,145)`.

### `ultralytics-ppe-nov2026-034.jpg` — 2048×2048

The foreground-left worker wears a yellow hard hat; the two nearer workers at center-right and right have uncovered gray hair. Behind them, a worker facing away wears a light hard hat. Two additional background heads are identifiable but too soft and small to classify confidently.

- Confirmed `hard_hat_worn`: foreground-left, xywh≈`(0.2539, 0.1074, 0.1147, 0.1147)`; px≈`(520,220,235,235)`.
- Confirmed `hard_hat_worn`: background worker facing away, xywh≈`(0.4907, 0.2319, 0.0513, 0.0659)`; px≈`(1005,475,105,135)`.
- Confirmed `bare_head`: center-right worker, xywh≈`(0.5884, 0.1855, 0.0854, 0.1025)`; px≈`(1205,380,175,210)`.
- Confirmed `bare_head`: foreground-right worker, xywh≈`(0.7080, 0.1318, 0.1025, 0.1221)`; px≈`(1450,270,210,250)`.
- Uncertain class, likely two separate blurred background people; approximate head boxes: xywh≈`(0.3320, 0.2539, 0.0415, 0.0586)`; px≈`(680,520,85,120)`, and xywh≈`(0.3784, 0.2637, 0.0439, 0.0610)`; px≈`(775,540,90,125)`. Headwear cannot be distinguished at this resolution.

### `ultralytics-ppe-nov2026-563.jpg` — 2048×2048

Two workers are visible. Both wear blue hard hats. The left worker and hat are cut off by the left and top image borders; the helmet remains identifiable.

- Confirmed `hard_hat_worn`: cropped left worker, xywh≈`(0.0000, 0.0000, 0.0659, 0.0928)`; px≈`(0,0,135,190)`.
- Confirmed `hard_hat_worn`: center worker, xywh≈`(0.4932, 0.0488, 0.1270, 0.1538)`; px≈`(1010,100,260,315)`.

### `source-c715790ce68e51f46da3fef5c618486a.jpg` — 2048×1360

Two distant workers are visible on the rebar deck. The left worker has a dark blue-gray billed cap; the nearer worker at center-right has dark uncovered hair. Their small size makes the boxes coarse.

- Confirmed `cap_worn`: far-left worker, xywh≈`(0.2051, 0.3125, 0.0366, 0.0662)`; px≈`(420,425,75,90)`.
- Confirmed `bare_head`: center-right worker, xywh≈`(0.4541, 0.4044, 0.0415, 0.0735)`; px≈`(930,550,85,100)`.

### `ultralytics-ppe-nov2026-490.jpg` — 2048×1152

One worker is cropped at the upper-right edge. The visible brim, shell, and side of a white hard hat sit directly above the face; this is a hard hat, not a bare head. The helmet crown is clipped by the frame edge.

- Confirmed `hard_hat_worn`: upper-right cropped worker, xywh≈`(0.6787, 0.0000, 0.1074, 0.1649)`; px≈`(1390,0,220,190)`.

### `ultralytics-ppe-nov2026-002.jpg` — 2048×1152

Three workers are visible in the foreground: left and right wear blue hard hats; the center worker has a bald/uncovered head.

- Confirmed `hard_hat_worn`: left, xywh≈`(0.1733, 0.0781, 0.1367, 0.2604)`; px≈`(355,90,280,300)`.
- Confirmed `bare_head`: center, xywh≈`(0.3809, 0.0955, 0.0757, 0.1997)`; px≈`(780,110,155,230)`.
- Confirmed `hard_hat_worn`: right, xywh≈`(0.6836, 0.0781, 0.1270, 0.2691)`; px≈`(1400,90,260,310)`.

### `ultralytics-ppe-nov2026-033.jpg` — 1152×2048

Three foreground workers wear yellow, white, and blue hard hats. Blurred background people are present; their headwear is too small/soft to classify or tightly localize.

- Confirmed `hard_hat_worn`: left, xywh≈`(0.1389, 0.2124, 0.1780, 0.1318)`; px≈`(160,435,205,270)`.
- Confirmed `hard_hat_worn`: center, xywh≈`(0.4340, 0.2246, 0.1562, 0.1270)`; px≈`(500,460,180,260)`.
- Confirmed `hard_hat_worn`: right, xywh≈`(0.7161, 0.1904, 0.1910, 0.1465)`; px≈`(825,390,220,300)`.
- Uncertain class: at least two background heads are visible behind the foreground group; no tight box/class proposal because blur and overlap prevent reliable bounds.

### `ultralytics-ppe-nov2026-097.jpg` — 2048×1360

Three people stand in the open wood-frame scene: the center worker wears a blue hard hat; the left and right men have uncovered gray hair.

- Confirmed `bare_head`: left, xywh≈`(0.2539, 0.1765, 0.0928, 0.1544)`; px≈`(520,240,190,210)`.
- Confirmed `hard_hat_worn`: center, xywh≈`(0.3857, 0.1691, 0.0977, 0.1838)`; px≈`(790,230,200,250)`.
- Confirmed `bare_head`: right, xywh≈`(0.5518, 0.1728, 0.0928, 0.1544)`; px≈`(1130,235,190,210)`.

### `ultralytics-ppe-nov2026-502.jpg` — 2048×1152

One centered worker wears a draped gray head covering that frames the face and continues down the neck/shoulders. The image does not support `beanie_worn`; this covering is outside the listed headwear classes, so leave it unresolved rather than force a class.

- Uncertain class: centered head/head covering, xywh≈`(0.4492, 0.0391, 0.1123, 0.2865)`; px≈`(920,45,230,330)`. The box is approximate and should be reviewed against the ontology boundary.

### `ultralytics-ppe-nov2026-339.jpg` — 2048×1360

Three people are visible: the left woman has uncovered hair; the center and right workers wear yellow hard hats.

- Confirmed `bare_head`: left, xywh≈`(0.3711, 0.1507, 0.0781, 0.1544)`; px≈`(760,205,160,210)`.
- Confirmed `hard_hat_worn`: center, xywh≈`(0.6152, 0.0772, 0.0830, 0.1691)`; px≈`(1260,105,170,230)`.
- Confirmed `hard_hat_worn`: right, xywh≈`(0.7959, 0.0882, 0.0830, 0.1691)`; px≈`(1630,120,170,230)`.

### `ultralytics-ppe-nov2026-378.jpg` — 1360×2048

Two workers are visible in the doorway: the standing worker at right wears a white hard hat; the bending worker at left also wears a white hard hat.

- Confirmed `hard_hat_worn`: standing-right, xywh≈`(0.6250, 0.0488, 0.1397, 0.1611)`; px≈`(850,100,190,330)`.
- Confirmed `hard_hat_worn`: bending-left, xywh≈`(0.2794, 0.3760, 0.1618, 0.1367)`; px≈`(380,770,220,280)`.

### `ultralytics-ppe-nov2026-072.jpg` — 2048×1360

One worker is visible indoors, wearing a green hard hat. The helmet touches the top frame edge.

- Confirmed `hard_hat_worn`: center, xywh≈`(0.4639, 0.0000, 0.1294, 0.2022)`; px≈`(950,0,265,275)`.

## Summary

- 13/13 original images reviewed; listed hashes and dimensions matched the roster.
- 32 heads have a visually supportable class and approximate box: 22 `hard_hat_worn`, 1 `cap_worn`, and 9 `bare_head`.
- 5 further heads remain uncertain: four blurred background heads in 034/033 and the out-of-ontology draped covering in 502. Exact localization is weak for the four background heads; those are not proposed as confirmed annotations.
- All 13 appear to be real photographic scenes. No visible people in depiction surfaces were found; no depiction-region boxes are proposed.
- No JSON, label, group, split, converter, or training changes were made.

## Source integrity

| File | Dimensions | SHA-256 |
|---|---:|---|
| `source-c285b53fb701de95fbfe70714765e8c7.jpg` | 1536×1024 | `5e80704990f94f5053372eaf2f46ae9fa45d9d9276bcd90fbe7808b7cce9194c` |
| `source-cdc3f2865204a12157c3f233e5f9bfaf.jpg` | 2048×1360 | `b94965fad5549c0a1610cb10514a98924e6f426b3874485614540feeae615e6b` |
| `ultralytics-ppe-nov2026-034.jpg` | 2048×2048 | `6f3b810087fadb286759e512d7d63d4806cfdaaf88eb47cef3015e8b7f209692` |
| `ultralytics-ppe-nov2026-563.jpg` | 2048×2048 | `baa663b3c64ac2ab71daa36c40341e59b399716b6407fc7913d8d7eabcf44ef9` |
| `source-c715790ce68e51f46da3fef5c618486a.jpg` | 2048×1360 | `14b60296f00a3a13c557d0d003f59efc0819cc7d14b6d16899e2ad417dff1dd3` |
| `ultralytics-ppe-nov2026-490.jpg` | 2048×1152 | `5e9614384efc6869f614a7250be995e84d34649e6cef712093a1eb24e0d92402` |
| `ultralytics-ppe-nov2026-002.jpg` | 2048×1152 | `e18092e2a401f842394c17e5ffa098e8b8038aff5e5d19cee689c6efae9152a4` |
| `ultralytics-ppe-nov2026-033.jpg` | 1152×2048 | `cae9cd2c1a0c538bd1ebbf53b2f73121992e7bf255cb341fd99919f68f2a7b50` |
| `ultralytics-ppe-nov2026-097.jpg` | 2048×1360 | `8f8e36e9cd592b419f56efa83800cbe630371b850df8ed5ba9c8592d084c4b3f` |
| `ultralytics-ppe-nov2026-502.jpg` | 2048×1152 | `b6b1fb583169c3ecda31ff13967c8c80d7e97c4feaf0b2fe673599e361499963` |
| `ultralytics-ppe-nov2026-339.jpg` | 2048×1360 | `ca336d5d01e931817a27e6e9e1f7fcaa8b35f9b1d526b5213c86ad512e830414` |
| `ultralytics-ppe-nov2026-378.jpg` | 1360×2048 | `c04d78075e82a80e7c0c935b3898d622307c462113ecb9348cae5bac8a9b3916` |
| `ultralytics-ppe-nov2026-072.jpg` | 2048×1360 | `dac25a02d150964010272f57f2e98225630caf94b1621324479a1659f03a0ca1` |
