package main

type creatorExperienceStep string

const (
	creatorStepConnect  creatorExperienceStep = "connect-usb"
	creatorStepSelect   creatorExperienceStep = "select-usb"
	creatorStepReview   creatorExperienceStep = "review-and-confirm"
	creatorStepCreating creatorExperienceStep = "creating-ordax"
	creatorStepComplete creatorExperienceStep = "complete"
	creatorStepBlocked  creatorExperienceStep = "blocked"
)

type creatorExperienceInput struct {
	TargetCount   int
	TargetSelected bool
	PhysicalReady bool
	WriteActive   bool
	WriteComplete bool
	Error         string
}

type creatorExperienceView struct {
	Step             creatorExperienceStep
	StepNumber       int
	StepCount        int
	Eyebrow          string
	Title            string
	Body             string
	Detail           string
	PrimaryAction    string
	SecondaryAction  string
	Illustration     string
	Destructive      bool
	CanContinue      bool
}

func creatorExperience(input creatorExperienceInput) creatorExperienceView {
	const steps = 4

	if input.Error != "" {
		return creatorExperienceView{
			Step:            creatorStepBlocked,
			StepNumber:      0,
			StepCount:       steps,
			Eyebrow:         "Precisamos da sua atenção",
			Title:           "Não foi possível continuar",
			Body:            "O Creator interrompeu o processo antes de fazer algo inseguro.",
			Detail:          input.Error,
			PrimaryAction:   "Tentar novamente",
			SecondaryAction: "Fechar",
			Illustration:    "shield-alert",
		}
	}

	if input.WriteComplete {
		return creatorExperienceView{
			Step:            creatorStepComplete,
			StepNumber:      steps,
			StepCount:       steps,
			Eyebrow:         "Tudo pronto",
			Title:           "Seu OrdaX USB foi criado",
			Body:            "O pendrive foi preparado e verificado. Agora você pode reiniciar o computador e iniciar pelo USB.",
			Detail:          "Se o computador não iniciar pelo pendrive automaticamente, abra o menu de boot da máquina e escolha o USB.",
			PrimaryAction:   "Concluir",
			SecondaryAction: "Como iniciar pelo USB",
			Illustration:    "usb-ready",
			CanContinue:     true,
		}
	}

	if input.WriteActive {
		return creatorExperienceView{
			Step:           creatorStepCreating,
			StepNumber:     steps,
			StepCount:      steps,
			Eyebrow:        "Criando o OrdaX USB",
			Title:          "Não remova o pendrive",
			Body:           "O Creator está preparando, gravando e verificando o OrdaX automaticamente.",
			Detail:         "A verificação final relê os arquivos gravados para confirmar integridade antes de concluir.",
			Illustration:   "write-progress",
			CanContinue:    false,
		}
	}

	if input.TargetCount == 0 {
		return creatorExperienceView{
			Step:            creatorStepConnect,
			StepNumber:      1,
			StepCount:       steps,
			Eyebrow:         "Etapa 1 de 4",
			Title:           "Conecte um pendrive USB",
			Body:            "Use um pendrive que possa ser apagado. O Creator encontra dispositivos USB compatíveis automaticamente.",
			Detail:          "Os discos internos do computador não são oferecidos como destino pelo Creator.",
			PrimaryAction:   "Recarregar USB",
			Illustration:    "usb-connect",
			CanContinue:     false,
		}
	}

	if !input.TargetSelected {
		return creatorExperienceView{
			Step:            creatorStepSelect,
			StepNumber:      2,
			StepCount:       steps,
			Eyebrow:         "Etapa 2 de 4",
			Title:           "Escolha o pendrive",
			Body:            "Confira nome e capacidade antes de continuar. Somente o USB escolhido poderá ser apagado.",
			Detail:          "O Creator revalida a identidade do dispositivo novamente antes da gravação.",
			PrimaryAction:   "Continuar",
			SecondaryAction: "Recarregar USB",
			Illustration:    "usb-select",
			CanContinue:     false,
		}
	}

	if !input.PhysicalReady {
		return creatorExperienceView{
			Step:            creatorStepBlocked,
			StepNumber:      3,
			StepCount:       steps,
			Eyebrow:         "Criação indisponível",
			Title:           "Este Creator ainda não pode gravar o USB",
			Body:            "O pendrive foi detectado com segurança, mas este canal do Creator não possui autorização física para criar uma mídia Stable/MVP.",
			Detail:          "Nenhuma alteração foi feita no pendrive.",
			PrimaryAction:   "Recarregar",
			Illustration:    "shield-lock",
			CanContinue:     false,
		}
	}

	return creatorExperienceView{
		Step:            creatorStepReview,
		StepNumber:      3,
		StepCount:       steps,
		Eyebrow:         "Etapa 3 de 4",
		Title:           "Revise antes de criar",
		Body:            "O pendrive selecionado será apagado e preparado para executar o OrdaX diretamente pelo USB.",
		Detail:          "O Creator não instala nada no SSD ou HD interno. Depois da confirmação, o Windows ainda solicitará autorização administrativa (UAC).",
		PrimaryAction:   "Criar OrdaX",
		SecondaryAction: "Voltar",
		Illustration:    "shield-check",
		Destructive:     true,
		CanContinue:     true,
	}
}
