The Escapists - ajuste experimental de resolucao 640x480
=========================================================

1. Copie a pasta "fixes" para dentro de:
   /roms/ports/theescapists/

   O resultado deve ser:
   /roms/ports/theescapists/fixes/libresolution_fix.so

2. No launch.sh, NAO use 960x720 no Weston. Use:

   WESTON_HEADLESS_WIDTH=640
   WESTON_HEADLESS_HEIGHT=480

3. Na lista de variaveis que vem depois de "crusty_glx_gl4es", antes da
   linha BOX64_LD_LIBRARY_PATH, acrescente:

   BOX64_LD_PRELOAD="$GAMEDIR/fixes/libresolution_fix.so" \

4. A parte final do comando deve ficar parecida com isto:

   BOX64_LOG=1 \
   BOX64_DYNAREC=1 \
   BOX64_EMULATED_LIBS="libSDL2-2.0.so.0" \
   BOX64_LD_PRELOAD="$GAMEDIR/fixes/libresolution_fix.so" \
   BOX64_LD_LIBRARY_PATH="$GAME_DIR/bin64:$GAME_DIR/lib64:$GAME_DIR/lib" \
   "$BOX64" "$GAME"

5. Execute o jogo e confira o novo log. Se o ajuste foi carregado, aparecera:

   [resolution_fix] SDL_SetWindowSize 960x720 -> 640x480

Esta biblioteca e x86_64 de proposito: ela e carregada dentro do programa
x86_64 pelo Box64. Nao substitua a SDL2 nem o executavel Chowdren.
