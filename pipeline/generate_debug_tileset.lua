local output_path = app.params.output
if not output_path or output_path == "" then
  error("Missing --script-param output=<path>")
end

local TILE_SIZE = 16
local GRID = 4
local SHEET_SIZE = TILE_SIZE * GRID
local PHASES = 8
local TILE_COUNT = GRID * GRID

-- Slot -> logical marching case ID. Shared with export_from_aseprite.py;
-- canonical values live in blob_layout.json (sibling to this script).
local script_dir = app.fs.filePath(debug.getinfo(1, "S").source:sub(2))
local layout_path = app.fs.joinPath(script_dir, "blob_layout.json")
local layout_file = assert(io.open(layout_path, "r"), "Failed to open " .. layout_path)
local layout_ok, BLOB_SLOT_TO_CASE = pcall(json.decode, layout_file:read("*a"))
layout_file:close()
if not layout_ok then
  error("Failed to parse blob_layout.json: " .. tostring(BLOB_SLOT_TO_CASE))
end

local TWO_PI = math.pi * 2

local function clamp01(value)
  if value < 0 then return 0 end
  if value > 1 then return 1 end
  return value
end

local function mix(a, b, t)
  return a + (b - a) * t
end

local function rgb(r, g, b)
  return Color {
    r = math.floor(r + 0.5),
    g = math.floor(g + 0.5),
    b = math.floor(b + 0.5),
    a = 255,
  }
end

-- Keep colors stable across phases; animation is done by moving the shoreline.
local GROUND_COLOR = rgb(148, 113, 74)
local WATER_COLOR = rgb(52, 142, 235)
local SHORE_HIGHLIGHT = rgb(192, 224, 242)

local function has_bit(value, bit)
  return math.floor(value / bit) % 2 == 1
end

local function corner_values(case_id)
  local nw = has_bit(case_id, 1) and 1 or 0
  local ne = has_bit(case_id, 2) and 1 or 0
  local se = has_bit(case_id, 4) and 1 or 0
  local sw = has_bit(case_id, 8) and 1 or 0
  return nw, ne, se, sw
end

local function bilinear(nw, ne, se, sw, u, v)
  local top = mix(nw, ne, u)
  local bottom = mix(sw, se, u)
  return mix(top, bottom, v)
end

local function draw_tile(img, slot_index, case_id, phase)
  local col = slot_index % GRID
  local row = math.floor(slot_index / GRID)
  local ox = col * TILE_SIZE
  local oy = row * TILE_SIZE

  local nw, ne, se, sw = corner_values(case_id)

  for py = 0, TILE_SIZE - 1 do
    for px = 0, TILE_SIZE - 1 do
      local u = (px + 0.5) / TILE_SIZE
      local v = (py + 0.5) / TILE_SIZE

      local base = bilinear(nw, ne, se, sw, u, v)

      -- Wavy shoreline motion: phase offsets move boundary pixels over time.
      local phase_t = phase / PHASES
      local wave =
        math.sin((u * 2.6 + v * 1.9 + phase_t) * TWO_PI)
        + 0.5 * math.sin((u * 5.4 - v * 3.1 - phase_t * 1.7) * TWO_PI)
      wave = wave / 1.5

      -- Keep wave influence at transition bands only.
      local edge_strength = clamp01(base * (1 - base) * 4)
      local effective = base + wave * 0.18 * edge_strength
      local inside = effective >= 0.5

      local color = inside and WATER_COLOR or GROUND_COLOR

      -- Thin bright shoreline accent near threshold.
      if edge_strength > 0.2 and math.abs(effective - 0.5) < 0.06 then
        color = SHORE_HIGHLIGHT
      end

      img:drawPixel(ox + px, oy + py, color)
    end
  end
end

local function draw_sheet(phase)
  local img = Image(SHEET_SIZE, SHEET_SIZE, ColorMode.RGB)
  for slot_index = 0, TILE_COUNT - 1 do
    local case_id = BLOB_SLOT_TO_CASE[slot_index + 1]
    if case_id == nil then
      error("Missing BLOB_SLOT_TO_CASE entry for slot " .. tostring(slot_index))
    end
    draw_tile(img, slot_index, case_id, phase)
  end
  return img
end

local sprite = Sprite(SHEET_SIZE, SHEET_SIZE, ColorMode.RGB)
for frame_index = 2, PHASES do
  sprite:newEmptyFrame(frame_index)
end

for _, frame in ipairs(sprite.frames) do
  frame.duration = 120
end

local layer = sprite:newLayer()
layer.name = "tilesets.debug.environment.autotile-15"

for frame_index = 1, PHASES do
  local phase = frame_index - 1
  sprite:newCel(layer, sprite.frames[frame_index], draw_sheet(phase), Point(0, 0))
end

local tag = sprite:newTag(1, PHASES)
tag.name = "tilesets.debug.environment.autotile-15"

sprite:saveAs(output_path)
app.exit()
