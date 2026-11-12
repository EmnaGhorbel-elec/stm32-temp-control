/*
 * stm_Cdriver.cpp
 *
 *  Created on: Jan 22, 2026
 *      Author: gabsi
 */
#include "stm_Cdriver.hpp"

void stm_gpioGr::stm_init(
		uint16_t pins ,
		uint32_t mode ,
		uint32_t alternate ,
		uint32_t pull ,
		uint32_t speed  ){
	GPIO_InitTypeDef GP;
	GP.Pin = pins ;
	GP.Mode = mode;
	GP.Pull = pull ;
	GP.Speed = speed ;
	GP.Alternate = alternate ;
	HAL_GPIO_Init(_port,&GP);
	/* if ((mode == GPIO_MODE_IT_RISING) || (mode == GPIO_MODE_IT_FALLING) || (mode == GPIO_MODE_IT_RISING_FALLING))
	{
		HAL_NVIC_SetPriority(pins +5,0,0); // EXIx_IRQnx = pins +5
		HAL_NVIC_EnableIRQ(EXTI0_IRQn);
		GPIO_PIN_

	}*/

}

void stm_gpioGr::stm_write(uint16_t pins,GPIO_PinState value){
	HAL_GPIO_WritePin(_port,pins,value);
}


GPIO_PinState stm_gpioGr::stm_read(uint16_t pin) {
	HAL_GPIO_ReadPin(_port,pin);
	return HAL_GPIO_ReadPin(_port,pin);
}

void stm_gpioGr::stm_toggle(uint16_t pins){
	HAL_GPIO_TogglePin(_port,pins);
}
// les methodes de la Classe  timer de base
void stm_basetimer::baseinit(uint32_t period,
							 uint32_t pscal ,
							 uint32_t countmode ){

	  _htim.Instance = _timer;
	  _htim.Init.Prescaler = pscal;
	  _htim.Init.CounterMode = countmode;
	  _htim.Init.Period = period;
	  _htim.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
	  _htim.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;

	  HAL_TIM_Base_Init(&_htim);

}

// Méthodes de manipulation
void stm_basetimer::basestart(void){
	__HAL_TIM_ENABLE(&_htim);
}
void stm_basetimer::basestop(void){
	__HAL_TIM_DISABLE(&_htim);
}
void stm_basetimer::basestart_IT(void) {
    __HAL_TIM_ENABLE_IT(&_htim,TIM_IT_UPDATE);
}

void stm_basetimer::basestop_IT(void) {
	__HAL_TIM_DISABLE_IT(&_htim,TIM_IT_UPDATE);
}



// PWM
void stm_pwmtimer::pwminit(uint32_t period, uint32_t pscal,uint32_t countmode,uint32_t channel) {

    this->baseinit(period, pscal,TIM_COUNTERMODE_UP);

    TIM_OC_InitTypeDef sConfigOC = {0};

        sConfigOC.OCMode = TIM_OCMODE_PWM1; // Mode standard
        sConfigOC.Pulse = 2000;            // Valeur de comparaison (CCR)
        sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
        sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;

        HAL_TIM_PWM_ConfigChannel(&_htim, &sConfigOC, channel);
}


void stm_pwmtimer::startchannel(uint32_t channel) {
    HAL_TIM_PWM_Start(&_htim, channel);
}

void stm_pwmtimer::stopchannel(uint32_t channel) {
    HAL_TIM_PWM_Stop(&_htim, channel);
}

void stm_pwmtimer::setdutycycle(uint32_t channel, uint32_t pulse) {
    // Macro ultra-rapide pour changer le registre CCRx
    __HAL_TIM_SET_COMPARE(&_htim, channel, pulse);
}


//---------------------- ADC

void stm_adc_group::init() {
    // Configuration de l'ADC
    _hadc.Init.ClockPrescaler        = ADC_CLOCK_SYNC_PCLK_DIV4;
    _hadc.Init.Resolution            = ADC_RESOLUTION_12B;
    _hadc.Init.ScanConvMode          = ENABLE;              // On veut parcourir une liste
    _hadc.Init.ContinuousConvMode    = DISABLE;             // Pas de boucle infinie
    _hadc.Init.DiscontinuousConvMode = ENABLE;              // On découpe le groupe
    _hadc.Init.NbrOfDiscConversion   = 1;                   // 1 conversion par déclenchement
    _hadc.Init.NbrOfConversion       = 2;                   // Taille totale du groupe
    _hadc.Init.ExternalTrigConv      = ADC_SOFTWARE_START;
    _hadc.Init.DataAlign             = ADC_DATAALIGN_RIGHT;
    _hadc.Init.EOCSelection          = ADC_EOC_SINGLE_CONV; // IT après chaque canal

    HAL_ADC_Init(&_hadc);

    // Configuration des Rangs du groupe
    ADC_ChannelConfTypeDef sConfig = {0};
    sConfig.SamplingTime = ADC_SAMPLETIME_15CYCLES;

    // Rang 1
    sConfig.Channel = _channels[0];
    sConfig.Rank = 1;
    HAL_ADC_ConfigChannel(&_hadc, &sConfig);

    // Rang 2
    sConfig.Channel = _channels[1];
    sConfig.Rank = 2;
    HAL_ADC_ConfigChannel(&_hadc, &sConfig);
}

void stm_adc_group::enableInterrupt(uint32_t priority) {
    HAL_NVIC_SetPriority(ADC_IRQn, priority, 0);
    HAL_NVIC_EnableIRQ(ADC_IRQn);
}

void stm_adc_group::startNextConversionIT() {
    HAL_ADC_Start_IT(&_hadc);
}

uint32_t stm_adc_group::getValue() {
    return HAL_ADC_GetValue(&_hadc);
}

//--------------------  UART

void stm_uart::init(uint32_t baudRate, uint32_t wordLength, uint32_t stopBits, uint32_t parity) {
	_huart.Instance = _uart;
	_huart.Init.BaudRate     = baudRate;
    _huart.Init.WordLength   = wordLength;
    _huart.Init.StopBits     = stopBits;
    _huart.Init.Parity       = parity;
    _huart.Init.Mode         = UART_MODE_TX_RX;
    _huart.Init.HwFlowCtl    = UART_HWCONTROL_NONE;
    _huart.Init.OverSampling = UART_OVERSAMPLING_16;

    HAL_UART_Init(&_huart);
}

void stm_uart::send(std::string message) {
    HAL_UART_Transmit(&_huart, (uint8_t*)message.c_str(), message.length(), HAL_MAX_DELAY);
}

void stm_uart::send(uint8_t* pData, uint16_t size) {
    HAL_UART_Transmit(&_huart, pData, size, HAL_MAX_DELAY);
}

HAL_StatusTypeDef stm_uart::receive(uint8_t* pBuffer, uint16_t size, uint32_t timeout) {
    return HAL_UART_Receive(&_huart, pBuffer, size, timeout);
}
