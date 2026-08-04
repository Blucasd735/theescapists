The Escapists - ajuste experimental de resolucao 640x480
=========================================================

1. pasta "fixes" correção de controles e resolução forçada:
   /roms/ports/theescapists/fixes

   O resultado deve ser:
   /roms/ports/theescapists/fixes/libresolution_fix.so

2. Correção no launch.sh, assim irá manter a resolução ideal da tela portátil:

   WESTON_HEADLESS_WIDTH=640
   WESTON_HEADLESS_HEIGHT=480

3. Na lista de variaveis que vem depois de "crusty_glx_gl4es", antes da
   linha BOX64_LD_LIBRARY_PATH vem a correção do patch melhorando a resolução correta:

   BOX64_LD_PRELOAD="$GAMEDIR/fixes/libresolution_fix.so" \

4. A parte final do comando deve ficar parecida com isto, assim temos a biblioteca do game e corrigido a resolução como o chamativo do box64 AARCH64:

   BOX64_LOG=1 \
   BOX64_DYNAREC=1 \
   BOX64_EMULATED_LIBS="libSDL2-2.0.so.0" \
   BOX64_LD_PRELOAD="$GAMEDIR/fixes/libresolution_fix.so" \
   BOX64_LD_LIBRARY_PATH="$GAME_DIR/bin64:$GAME_DIR/lib64:$GAME_DIR/lib" \
   "$BOX64" "$GAME"

Esta biblioteca e x86_64 de proposito: ela e carregada dentro do programa
x86_64 pelo Box64. Nao substitua a SDL2 nem o executavel Chowdren.
