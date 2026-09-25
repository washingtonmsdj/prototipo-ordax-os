package main

func creatorBootHelpText() string {
	return "Como iniciar pelo OrdaX USB\n\n" +
		"1. Deixe o pendrive OrdaX conectado ao computador.\n" +
		"2. Reinicie o computador.\n" +
		"3. Abra o menu de boot/UEFI da máquina. A tecla varia conforme o fabricante.\n" +
		"4. Escolha o dispositivo USB/UEFI correspondente ao pendrive OrdaX.\n" +
		"5. O OrdaX inicia diretamente pelo USB; o Creator não instala o sistema no SSD ou HD interno.\n\n" +
		"Se o USB não aparecer, verifique no firmware se a inicialização por USB está habilitada e tente outra porta USB."
}
