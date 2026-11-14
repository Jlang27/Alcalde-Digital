@echo off
rem  Abre el puerto del multijugador de Alcalde Digital en el firewall de
rem  Windows. Hay que hacerlo UNA vez en el PC que hostea la partida.
rem
rem  Por que hace falta: la primera vez que el juego abre el puerto, Windows
rem  pregunta si lo deja pasar, y en una red marcada como «publica» (la de
rem  una feria casi siempre) lo bloquea aunque se le diga que si. El otro PC
rem  solo ve «Nadie contesta en esa dirección».
rem
rem  Uso: clic derecho -> «Ejecutar como administrador».

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  Hay que ejecutarlo como administrador:
    echo  clic derecho sobre este archivo -^> «Ejecutar como administrador».
    echo.
    pause
    exit /b 1
)

netsh advfirewall firewall delete rule name="Alcalde Digital (multijugador)" >nul 2>&1
netsh advfirewall firewall add rule name="Alcalde Digital (multijugador)" ^
    dir=in action=allow protocol=TCP localport=5050 profile=any
if %errorlevel% neq 0 (
    echo  No se pudo crear la regla.
    pause
    exit /b 1
)

echo.
echo  Listo: el puerto 5050 queda abierto en redes privadas y publicas.
echo  Si aun asi el otro PC no conecta, la red bloquea a los equipos entre
echo  si (pasa en muchas wifi de eventos): conectad los dos PC al punto de
echo  acceso de un celular, o con un cable.
echo.
pause
