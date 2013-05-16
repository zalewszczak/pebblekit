#include "pebble_os.h"
#include "pebble_app.h"
#include "pebble_fonts.h"
#include "resource_ids.auto.h"
#include <stdint.h>
#include <string.h>

#define BITMAP_BUFFER_BYTES 1024

// 42c86ea4-1c3e-4a07-b889-2cccca914198
#define MY_UUID {0x42, 0xc8, 0x6e, 0xa4, 0x1c, 0x3e, 0x4a, 0x7, 0xb8, 0x89, 0x2c, 0xcc, 0xca, 0x91, 0x41, 0x98}
PBL_APP_INFO(MY_UUID, "Pebble Weather", "Pebble Technology", 0x1, 0x0, DEFAULT_MENU_ICON, APP_INFO_STANDARD_APP);

static struct WeatherData {
  Window window;
  TextLayer temperature_layer;
  char temperature[16];
  BitmapLayer icon_layer;
  GBitmap icon_bitmap;
  uint8_t bitmap_data[BITMAP_BUFFER_BYTES];
  AppSync sync;
  uint8_t sync_buffer[32];
} s_data;

enum {
  WEATHER_ICON_KEY = 0x0,         // TUPLE_INT
  WEATHER_TEMPERATURE_KEY = 0x1,  // TUPLE_CSTRING
};

static uint32_t WEATHER_ICONS[] = {
  RESOURCE_ID_IMAGE_SUN,
  RESOURCE_ID_IMAGE_CLOUD,
  RESOURCE_ID_IMAGE_RAIN,
  RESOURCE_ID_IMAGE_SNOW
};

static void mkbitmap(GBitmap* bitmap, const uint8_t* data) {
  bitmap->addr = (void*)data + 12;
  bitmap->row_size_bytes = ((uint16_t*)data)[0];
  bitmap->info_flags = ((uint16_t*)data)[1];
  bitmap->bounds.origin.x = 0;
  bitmap->bounds.origin.y = 0;
  bitmap->bounds.size.w = ((int16_t*)data)[4];
  bitmap->bounds.size.h = ((int16_t*)data)[5];
}

static void load_bitmap(uint32_t resource_id) {
  const ResHandle h = resource_get_handle(resource_id);
  resource_load(h, s_data.bitmap_data, BITMAP_BUFFER_BYTES);
  mkbitmap(&s_data.icon_bitmap, s_data.bitmap_data);
}

// TODO: Error handling
static void sync_error_callback(DictionaryResult dict_error, AppMessageResult app_message_error, void *context) {
  (void) dict_error;
  (void) app_message_error;
  (void) context;
}

static void sync_tuple_changed_callback(const uint32_t key, const Tuple* new_tuple, const Tuple* old_tuple, void* context) {
  (void) old_tuple;

  switch (key) {
  case WEATHER_ICON_KEY:
    load_bitmap(WEATHER_ICONS[new_tuple->value->uint8]);
    layer_mark_dirty(&s_data.icon_layer.layer);
    break;
  case WEATHER_TEMPERATURE_KEY:
    strncpy(s_data.temperature, new_tuple->value->cstring, 16);
    layer_mark_dirty(&s_data.temperature_layer.layer);
    break;
  default:
    return;
  }
}

static void weather_app_init(AppContextRef c) {
  (void) c;

  resource_init_current_app(&WEATHER_APP_RESOURCES);

  Window* window = &s_data.window;
  window_init(window, "Weather");
  window_set_background_color(window, GColorBlack);
  window_set_fullscreen(window, true);

  GRect icon_rect = (GRect) {(GPoint) {32, 10}, (GSize) { 80, 80 }};
  bitmap_layer_init(&s_data.icon_layer, icon_rect);
  bitmap_layer_set_bitmap(&s_data.icon_layer, &s_data.icon_bitmap);
  layer_add_child(&window->layer, &s_data.icon_layer.layer);

  text_layer_init(&s_data.temperature_layer, GRect(0, 100, 144, 68));
  text_layer_set_text_color(&s_data.temperature_layer, GColorWhite);
  text_layer_set_background_color(&s_data.temperature_layer, GColorClear);
  text_layer_set_font(&s_data.temperature_layer, fonts_get_system_font(FONT_KEY_GOTHIC_28_BOLD));
  text_layer_set_text_alignment(&s_data.temperature_layer, GTextAlignmentCenter);
  text_layer_set_text(&s_data.temperature_layer, s_data.temperature);
  layer_add_child(&window->layer, &s_data.temperature_layer.layer);

  Tuplet initial_values[] = {
    TupletInteger(WEATHER_ICON_KEY, (uint8_t) 1),
    TupletCString(WEATHER_TEMPERATURE_KEY, "1234\u00B0C"),
  };
  app_sync_init(&s_data.sync, s_data.sync_buffer, sizeof(s_data.sync_buffer), initial_values, ARRAY_LENGTH(initial_values),
                sync_tuple_changed_callback, sync_error_callback, NULL);

  window_stack_push(window, true);
}

 static void weather_app_deinit(AppContextRef c) {
   app_sync_deinit(&s_data.sync);
 }

void pbl_main(void *params) {
  PebbleAppHandlers handlers = {
    .init_handler = &weather_app_init,
    .deinit_handler = &weather_app_deinit,
    .messaging_info = {
      .buffer_sizes = {
        .inbound = 64,
        .outbound = 16,
      }
    }
  };
  app_event_loop(params, &handlers);
}
