# 하나 내비 Design System Guidelines

## Typography System - Figma Inspired Bold Design

### Font Hierarchy - Adjusted Smaller
- **Display Text (H1)**: 56px, Extra Bold (800), for main headlines
- **Hero Text (H2)**: 32px, Bold (700), for section headers
- **Large Text (H3)**: 24px, Bold (700), for subsections
- **Body Large**: 16px, Normal (400), for descriptions
- **Regular Body**: 16px, Normal (400), for standard text

### Font Weights Available
- Normal: 400
- Medium: 500
- Semibold: 600
- Bold: 700
- Extra Bold: 800
- Black: 900

## Color System

### Primary Purple Gradient
- Primary: #8b5cf6 (violet-500)
- Accent: #6366f1 (indigo-500)
- Gradient: `linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%)`

### Card & Component Styling
- Enhanced cards use `card-enhanced` class with modern shadows
- Buttons use `button-primary` class with gradient backgrounds
- Hover effects include scale and shadow transformations

## Component Guidelines

### Buttons
- Use bold fonts (700+ weight) for all button text
- Primary buttons should use gradient backgrounds
- Include hover animations (scale and shadow)
- Round corners with large border-radius (24px+)

### Cards
- Use enhanced card styling with backdrop blur
- Apply subtle scale transforms on hover
- Include modern shadow system inspired by Figma design

### Typography
- Headlines should use gradient text effects when appropriate
- Maintain consistent letter spacing for readability
- Use font-semibold or font-bold for most UI elements

### Spacing & Layout
- Generous padding and margins for breathing room
- Large icon sizes (24px+) for visual impact
- Consistent gap spacing using multiples of 4px

## Interactive Elements

### Hover States
- Scale transformations (1.02-1.05)
- Enhanced shadow effects
- Color transitions with cubic-bezier easing
- Letter spacing adjustments for emphasis

### Focus States
- Visible outlines with brand colors
- Accessibility-compliant contrast ratios
- Smooth transition animations
<!--

System Guidelines

Use this file to provide the AI with rules and guidelines you want it to follow.
This template outlines a few examples of things you can add. You can add your own sections and format it to suit your needs

TIP: More context isn't always better. It can confuse the LLM. Try and add the most important rules you need

# General guidelines

Any general rules you want the AI to follow.
For example:

* Only use absolute positioning when necessary. Opt for responsive and well structured layouts that use flexbox and grid by default
* Refactor code as you go to keep code clean
* Keep file sizes small and put helper functions and components in their own files.

--------------

# Design system guidelines
Rules for how the AI should make generations look like your company's design system

Additionally, if you select a design system to use in the prompt box, you can reference
your design system's components, tokens, variables and components.
For example:

* Use a base font-size of 14px
* Date formats should always be in the format “Jun 10”
* The bottom toolbar should only ever have a maximum of 4 items
* Never use the floating action button with the bottom toolbar
* Chips should always come in sets of 3 or more
* Don't use a dropdown if there are 2 or fewer options

You can also create sub sections and add more specific details
For example:


## Button
The Button component is a fundamental interactive element in our design system, designed to trigger actions or navigate
users through the application. It provides visual feedback and clear affordances to enhance user experience.

### Usage
Buttons should be used for important actions that users need to take, such as form submissions, confirming choices,
or initiating processes. They communicate interactivity and should have clear, action-oriented labels.

### Variants
* Primary Button
  * Purpose : Used for the main action in a section or page
  * Visual Style : Bold, filled with the primary brand color
  * Usage : One primary button per section to guide users toward the most important action
* Secondary Button
  * Purpose : Used for alternative or supporting actions
  * Visual Style : Outlined with the primary color, transparent background
  * Usage : Can appear alongside a primary button for less important actions
* Tertiary Button
  * Purpose : Used for the least important actions
  * Visual Style : Text-only with no border, using primary color
  * Usage : For actions that should be available but not emphasized
-->
