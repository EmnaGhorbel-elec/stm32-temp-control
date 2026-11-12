/*
 * stm_Cdriver.hpp
 *
 *  Created on: Jan 22, 2026
 *      Author: WYNSYS
 */

#ifndef INC_STM_CDRIVER_HPP_
#define INC_STM_CDRIVER_HPP_
#include "stm32f4xx_hal.h"
#include <cstdint>

#include <iostream>
class stm_gpioGr
{
private :
	GPIO_TypeDef * _port ;
public :
	stm_gpioGr(GPIO_TypeDef * port):_port(port){}

	void stm_init(uint16_t pins ,uint32_t mode , uint32_t alternate = 0,uint32_t pull =GPIO_NOPULL ,uint32_t speed =GPIO_SPEED_FREQ_MEDIUM );
	void stm_write(uint16_t pins ,GPIO_PinState value);
	GPIO_PinState stm_read(uint16_t pin);
	void stm_toggle(uint16_t pins);
};



class stm_basetimer{
protected:
	TIM_TypeDef* _timer;
	TIM_HandleTypeDef _htim; // On stocke le handle ici
public:
    // Constructeur demandé
	stm_basetimer(TIM_TypeDef* timer) : _timer(timer) {}

	// Méthode de configuration groupée
	    void baseinit(uint32_t period, uint32_t pscal = 0,
	                uint32_t countmode = TIM_COUNTERMODE_UP);

	    // Méthodes de manipulation
	    void basestart(void);
	    void basestop(void);
	    // Contrôle avec Interruptions (IT)
	        void basestart_IT();
	        void basestop_IT();
	    TIM_HandleTypeDef* getHandle() { return &_htim; }

};


//PWM
class stm_pwmtimer : public stm_basetimer {
public:
    // Le constructeur appelle simplement celui de la base
    stm_pwmtimer(TIM_TypeDef* timer) : stm_basetimer(timer) {}

    // Initialisation spécifique au PWM
    void pwminit(uint32_t period, uint32_t pscal = 1,
    					uint32_t countmode = TIM_COUNTERMODE_UP,uint32_t channel = TIM_CHANNEL_1);

    // Démarrage/Arrêt spécifique au canal
    void startchannel(uint32_t channel);
    void stopchannel(uint32_t channel);

    // Modifier le rapport cyclique (Duty Cycle) à la volée
    void setdutycycle(uint32_t channel, uint32_t pulse);
};
// ----------------ADC
class stm_adc_group {
private:
	ADC_TypeDef* _adc;
    ADC_HandleTypeDef _hadc= {0};
    uint32_t _channels[2];

public:
    // Constructeur : on définit deux chaînes physiques
    stm_adc_group(ADC_TypeDef* adc, uint32_t ch1, uint32_t ch2):_adc(adc) {
        _hadc.Instance = _adc;
        _channels[0] = ch1;
        _channels[1] = ch2;
    }

    // Initialise l'ADC en mode SCAN + DISCONTINU
    void init();

    // Active l'interruption au niveau du NVIC
    void enableInterrupt(uint32_t priority = 0);

    // Lance UNE conversion (la suivante dans le groupe)
    void startNextConversionIT();

    // Lit la valeur convertie (à appeler dans l'interruption)
    uint32_t getValue();

    // Accesseur pour le handle (nécessaire pour le lien avec HAL)
    ADC_HandleTypeDef* getHandle() { return &_hadc; }
};
// -------UART
class stm_uart {
private:
    USART_TypeDef* _uart;
    UART_HandleTypeDef _huart;

public:
    // Constructeur défini directement dans le .hpp
    stm_uart(USART_TypeDef* uart) : _uart(uart) {}

    // Initialisation complète et simple
        void init(uint32_t baudRate,
                  uint32_t wordLength = UART_WORDLENGTH_8B,
                  uint32_t stopBits   = UART_STOPBITS_1,
                  uint32_t parity     = UART_PARITY_NONE);

        // Envoi de données (Mode bloquant simple)
        void send(std::string message);
        void send(uint8_t* pData, uint16_t size);

        // Réception de données (Mode bloquant avec timeout)
        HAL_StatusTypeDef receive(uint8_t* pBuffer, uint16_t size, uint32_t timeout = 100);

        // Accesseur
        UART_HandleTypeDef* getHandle() { return &_huart; }
    };



#endif /* INC_STM_CDRIVER_HPP_ */
