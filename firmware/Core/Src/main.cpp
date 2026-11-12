/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include <string>
#include <iostream>
#include <cstdio>
#include "stm_Cdriver.hpp"

#define Tcmin 50
#define Tcmax 70
#define PWM_MAX 16000

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
uint16_t regP(uint32_t tm, uint32_t tc);

/* USER CODE BEGIN 0 */

// GPIO & périphériques
stm_gpioGr LEDS(GPIOD), LEDR(GPIOD), Button(GPIOA),
           pb6pwm(GPIOB), uart5_TX(GPIOC), uart5_RX(GPIOD),
           adcpins(GPIOB);

stm_basetimer timer7(TIM7);
stm_pwmtimer tim4pwm(TIM4);
stm_uart uart5(UART5);
stm_adc_group adc01(ADC1, ADC_CHANNEL_8, ADC_CHANNEL_9);

// Variables globales
volatile bool affiche = false;
bool degCF = true; // true = Celsius, false = Fahrenheit (toggled by Button/EXTI0)
uint16_t mli = 200;
uint16_t lm35 = 0, pot = 0;

/* USER CODE END 0 */

int main(void)
{
    /* Activation des horloges */
    __HAL_RCC_GPIOD_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_TIM7_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_TIM4_CLK_ENABLE();
    __HAL_RCC_UART5_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_ADC1_CLK_ENABLE();

    HAL_Init();
    SystemClock_Config();

    /* ================== INIT ================== */

    // LEDs
    LEDS.stm_init(GPIO_PIN_12 | GPIO_PIN_13 | GPIO_PIN_14 | GPIO_PIN_15,
                  GPIO_MODE_OUTPUT_PP);

    LEDR.stm_init(GPIO_PIN_5, GPIO_MODE_OUTPUT_OD);

    // Bouton EXTI
    Button.stm_init(GPIO_PIN_0, GPIO_MODE_IT_RISING);
    HAL_NVIC_SetPriority(EXTI0_IRQn, 0, 0);
    HAL_NVIC_EnableIRQ(EXTI0_IRQn);

    // TIMER 7 (interruptions, 1 Hz control tick)
    timer7.baseinit(9999, 8399);
    timer7.basestart();
    timer7.basestart_IT();
    HAL_NVIC_SetPriority(TIM7_IRQn, 0, 0);
    HAL_NVIC_EnableIRQ(TIM7_IRQn);

    // PWM TIM4 (PB6) — drives the actuator
    pb6pwm.stm_init(GPIO_PIN_6, GPIO_MODE_AF_PP, GPIO_AF2_TIM4);
    tim4pwm.pwminit(PWM_MAX, 0, TIM_COUNTERMODE_UP, TIM_CHANNEL_1);
    tim4pwm.startchannel(TIM_CHANNEL_1);

    // UART5 — telemetry out
    uart5_RX.stm_init(GPIO_PIN_2, GPIO_MODE_AF_PP, GPIO_AF8_UART5, GPIO_PULLUP);
    uart5_TX.stm_init(GPIO_PIN_12, GPIO_MODE_AF_PP, GPIO_AF8_UART5, GPIO_PULLUP);
    uart5.init(9600);

    // ADC (LM35 + potentiometer)
    adcpins.stm_init(GPIO_PIN_0 | GPIO_PIN_1, GPIO_MODE_ANALOG);
    adc01.enableInterrupt(1);
    adc01.init();

    /* ================== LOOP ================== */
    while (1)
    {
        if (affiche)
        {
            char buffer[40];

            // LM35 output is 10 mV/°C; ADC is 12-bit over a 3.3 V reference
            uint32_t Tm = (uint32_t)lm35 * 3300 >> 12;
            Tm = Tm / 10;

            // Map potentiometer reading (0-4095) onto the [Tcmin, Tcmax] setpoint range
            uint32_t Tc = Tcmin + ((pot * (Tcmax - Tcmin)) >> 12);

            // Proportional control -> PWM duty cycle
            mli = regP(Tm, Tc);
            tim4pwm.setdutycycle(TIM_CHANNEL_1, mli);

            // Machine-readable telemetry line, parsed by the PC-side dashboard
            // Format: DATA:<Tm_celsius>,<Tc_celsius>,<pwm_value>
            std::snprintf(buffer, sizeof(buffer), "DATA:%lu,%lu,%d\r\n", Tm, Tc, mli);
            uart5.send(buffer);

            affiche = false;
        }
    }
}

/* ================= INTERRUPTIONS ================= */
extern "C"
{

void EXTI0_IRQHandler(void)
{
    if (__HAL_GPIO_EXTI_GET_FLAG(GPIO_PIN_0))
    {
        LEDR.stm_toggle(GPIO_PIN_5);
        degCF = !degCF;
        __HAL_GPIO_EXTI_CLEAR_FLAG(GPIO_PIN_0);
    }
}

void TIM7_IRQHandler(void)
{
    static uint8_t elon = 0;

    if (__HAL_TIM_GET_FLAG(timer7.getHandle(), TIM_IT_UPDATE))
    {
        LEDS.stm_toggle((GPIO_PIN_12 << elon));

        elon++;
        if (elon >= 4)
            elon = 0;

        adc01.startNextConversionIT();

        __HAL_TIM_CLEAR_FLAG(timer7.getHandle(), TIM_IT_UPDATE);
    }
}

void ADC_IRQHandler(void)
{
    static bool prem = true;

    if (__HAL_ADC_GET_FLAG(adc01.getHandle(), ADC_FLAG_EOC))
    {
        if (prem)
        {
            lm35 = adc01.getValue();
            adc01.startNextConversionIT();
            prem = false;
        }
        else
        {
            pot = adc01.getValue();
            prem = true;
        }

        affiche = true;
        __HAL_ADC_CLEAR_FLAG(adc01.getHandle(), ADC_FLAG_EOC);
    }
}
}

/* ================= P CONTROLLER ================= */
uint16_t regP(uint32_t tm, uint32_t tc)
{
    uint16_t kp = 800;
    uint32_t output = 0;

    if (tm > tc)
        output = kp * (tm - tc);

    // Saturation PWM
    if (output > PWM_MAX)
        output = PWM_MAX;

    return (uint16_t)output;
}

/* ================= CLOCK ================= */
void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    __HAL_RCC_PWR_CLK_ENABLE();
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    RCC_OscInitStruct.HSEState = RCC_HSE_ON;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    RCC_OscInitStruct.PLL.PLLM = 8;
    RCC_OscInitStruct.PLL.PLLN = 336;
    RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV2;
    RCC_OscInitStruct.PLL.PLLQ = 7;

    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
        Error_Handler();

    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
                               | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;

    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV4;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV2;

    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_5) != HAL_OK)
        Error_Handler();
}

/* ================= ERROR ================= */
void Error_Handler(void)
{
    __disable_irq();
    while (1) {}
}
