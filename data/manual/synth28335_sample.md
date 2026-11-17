# SYNTH-28335 Technical Reference Manual (Sample Excerpt)

> 本文件为**演示用合成语料**，仿照 TI C2000 类技术手册的写作与表格结构编写。
> 寄存器名沿用公开的 F28335 命名（GPAMUX1、GPADIR 等），但正文描述为自撰，不是 TI 原文。

## 1 GPIO

### 1.1 Overview

The GPIO module provides up to 88 individually configurable pins. Each pin can serve as
a general-purpose digital input/output or as one of several peripheral functions.
Configuration is performed through a set of memory-mapped registers grouped by port
(A, B, C).

zh: GPIO 模块提供最多 88 个可独立配置的引脚，每个引脚可作通用数字输入输出，或复用为若干外设功能之一，通过按端口分组的寄存器进行配置。

### 1.2 MUX Registers

The multiplexing registers GPAMUX1 and GPAMUX2 select the function of each pin on port A.
GPAMUX1 covers GPIO0 to GPIO15, two bits per pin. GPAMUX2 covers GPIO16 to GPIO31.
Writing 00 selects the general-purpose I/O function; other values select peripheral
functions as listed in the pin mux table.

| Bits | Field | Type | Reset | Description |
|---|---|---|---|---|
| 1-0 | GPIO0 | R/W | 0 | 00=GPIO, 01=EPWM1A, 10=reserved, 11=reserved |
| 3-2 | GPIO1 | R/W | 0 | 00=GPIO, 01=EPWM1B, 10=reserved, 11=reserved |
| 5-4 | GPIO2 | R/W | 0 | 00=GPIO, 01=EPWM2A, 10=reserved, 11=reserved |
| 31-30 | GPIO15 | R/W | 0 | 00=GPIO, 01=SPISIMOA, 10=reserved, 11=reserved |

zh: 复用寄存器 GPAMUX1/GPAMUX2 决定端口 A 每个引脚的功能；GPAMUX1 覆盖 GPIO0-GPIO15，每引脚两位，写 00 为通用 IO，其他值选择外设功能。

### 1.3 Direction and Data Registers

GPADIR configures the direction of each pin: 1 for output, 0 for input. GPADAT holds the
current level. For atomic updates use GPASET to drive high, GPACLEAR to drive low, and
GPATOGGLE to invert, which avoid read-modify-write races on shared ports.

| Register | Bits | Reset | Description |
|---|---|---|---|
| GPADIR | 31-0 | 0x0000 | 1=output, 0=input |
| GPADAT | 31-0 | 0x0000 | pin data, write only affects output pins |
| GPASET | 31-0 | 0x0000 | write 1 sets the corresponding output high |
| GPACLEAR | 31-0 | 0x0000 | write 1 drives the corresponding output low |
| GPATOGGLE | 31-0 | 0x0000 | write 1 inverts the corresponding output |

zh: GPADIR 配置方向，1 为输出 0 为输入；GPADAT 保存电平；GPASET/GPACLEAR/GPATOGGLE 提供原子置位、清零、翻转，避免读改写竞争。

### 1.4 Input Qualification

Input qualification filters noise on selected pins. GPxQSEL1 and GPxQSEL2 select the
sampling mode: synchronous, qualification with 3 samples, or qualification with 6
samples. GPACTRL defines the qualification sampling period QUALPRD, which sets the
interval between samples as a multiple of the system clock.

| Bits | Field | Type | Reset | Description |
|---|---|---|---|---|
| 7-0 | QUALPRD0 | R/W | 0x00 | qualification period for GPIO0-7, in SYSCLKOUT cycles |
| 15-8 | QUALPRD1 | R/W | 0x00 | qualification period for GPIO8-15 |
| 31-24 | QUALPRD3 | R/W | 0x00 | qualification period for GPIO24-31 |

zh: 输入限定用于滤除引脚噪声；GPxQSEL1/2 选择采样模式（同步、3 采样、6 采样），GPACTRL 中的 QUALPRD 定义采样周期。

### 1.5 Pull-up and Interrupt

GPAPUD enables or disables the internal pull-up on each pin, one bit per pin. GPIO
interrupts are configured through GPIOXINT1SEL and GPIOXINT2SEL, which route a selected
pin to XINT1 or XINT2. The interrupt polarity is set in the XINT control registers.

zh: GPAPUD 按位使能内部上拉；GPIO 中断通过 GPIOXINT1SEL/2SEL 把指定引脚路由到 XINT1/XINT2，极性在 XINT 控制寄存器中设置。

## 2 ePWM

### 2.1 Overview

The enhanced PWM module generates complex pulse width waveforms with minimal CPU
overhead. Each ePWM module consists of a time-base submodule, a counter-compare
submodule, an action-qualifier submodule, a dead-band generator, and an event-trigger
submodule.

zh: ePWM 模块以极低 CPU 开销产生复杂 PWM 波形，包含时基、计数比较、动作限定、死区和事件触发子模块。

### 2.2 Time-Base

TBPRD sets the period of the PWM counter. TBCTR is the current counter value. The
time-base clock prescaler divides SYSCLKOUT before driving the counter, and the counter
mode (up, down, up-down) determines the waveform symmetry.

| Register | Bits | Reset | Description |
|---|---|---|---|
| TBPRD | 15-0 | 0x0000 | time-base period, sets PWM frequency |
| TBCTR | 15-0 | 0x0000 | current time-base counter value |

zh: TBPRD 设置 PWM 周期，TBCTR 为当前计数值；时基预分频对系统时钟分频后驱动计数器。

### 2.3 Compare and Action Qualifier

CMPA and CMPB hold the compare values that define duty cycle. The action-qualifier
registers AQCTLA control what the output does on a compare match: set, clear, toggle,
or do nothing, depending on the counter direction.

| Bits | Field | Type | Reset | Description |
|---|---|---|---|---|
| 1-0 | ZRO | R/W | 0 | action on counter zero: 00=none, 01=clear, 10=set, 11=toggle |
| 3-2 | PRD | R/W | 0 | action on period match |
| 5-4 | CAU | R/W | 0 | action on compare A while counting up |
| 7-6 | CAD | R/W | 0 | action on compare A while counting down |

zh: CMPA/CMPB 定义占空比；AQCTLA 规定比较匹配时输出置位、清零、翻转或不动作。

### 2.4 ADC Start-of-Conversion Trigger

The event-trigger submodule can start an ADC conversion without CPU intervention.
ETSEL selects the event source and enables the SOCA or SOCB signal. When the selected
event occurs, the ePWM asserts SOCA, which is routed to the ADC trigger input.

zh: 事件触发子模块可在无需 CPU 干预的情况下启动 ADC 转换；ETSEL 选择事件源并开启 SOCA/SOCB 信号，事件发生时 ePWM 拉高 SOCA 送到 ADC 触发输入。

## 3 ADC

### 3.1 Overview

The analog-to-digital converter is a 12-bit successive-approximation converter with a
multiplexed input. Up to 16 channels are available, and conversions can be started by
software, by an ePWM SOC signal, or by an external pin.

zh: ADC 为 12 位逐次逼近型转换器，输入多路复用，最多 16 通道，可由软件、ePWM 的 SOC 信号或外部引脚启动转换。

### 3.2 Start-of-Conversion and Sequencer

ADCSOCxCTL configures each SOC: the trigger source TRIGSEL, the channel, and the
acquisition window ACQPS. The sequencer runs the configured SOCs in order and stores
results in ADCRESULT registers.

| Bits | Field | Type | Reset | Description |
|---|---|---|---|---|
| 4-0 | ACQPS | R/W | 0 | acquisition window in ADCCLK cycles, minus one |
| 11-8 | CHSEL | R/W | 0 | analog input channel select, 0-15 |
| 15-12 | TRIGSEL | R/W | 0 | trigger source: 0=software, 5=ePWM1 SOCA |

zh: ADCSOCxCTL 配置每次转换：TRIGSEL 选择触发源，CHSEL 选通道，ACQPS 设采样窗口；序列器按序执行并把结果存入 ADCRESULT。

### 3.3 Results

ADCRESULT0 through ADCRESULT15 hold the conversion results, right-justified 12-bit
values. Results must be read before the next conversion overwrites them unless the
sequencer is configured in a mode that preserves earlier results.

zh: ADCRESULT0-15 保存转换结果，为右对齐 12 位；若序列器未配置为保留模式，需在下一次转换覆盖前读取。

## 4 System Initialization

### 4.1 Reset and Clock Enable

After reset all peripherals are held in a low-power state. The PLLCR register sets the
PLL multiplier to derive SYSCLKOUT from the external crystal. The PCLKCR0, PCLKCR1 and
PCLKCR3 registers enable the clock to individual peripherals; a peripheral must be
clocked before its registers can be accessed reliably.

zh: 复位后外设处于低功耗状态；PLLCR 设置倍频得到 SYSCLKOUT；PCLKCR0/1/3 使能各外设时钟，访问寄存器前必须先开时钟。
