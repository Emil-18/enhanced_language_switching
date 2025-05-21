# Enhanced Language Detection

* Author: Emil-18
* NVDA compatibility: 2024.2 and beyond
* Download: [Stable version](https://github.com/Emil-18/enhanced_language_switching/releases/download/v1.1/enhancedLanguageDetection-1.1.nvda-addon).

This add-on Automaticly detects the language of the text NVDA is about to speak, and uses NVDA's built in auto language switching, if turned on, to sspeak the text in that language.

This add-on is heavily inspired by [the language ident add-on](https://github.com/slohmaier/LanguageIdent).
That add-on stopped working, however, and from it's issues on GitHub, it doesn't seam like the developer is going to fix it.

## Settings

* Language interpretation:
    This is a combo box that allows you to select when the add-on is interpreting the language of the text. The choices are:
    * always interpret:
        the add-on will always interpret the language of the text and remove all previous instructions to change the language. For example, if you are on a web page, and the language of the web page is defined as english, but according to the add-on, the text is Norwegian, it will switch to a Norwegian voice. If you haven't selected Norwegian as one of the languages to be interpreted, (see below), the voice will not change at all.
    * only interpret if the text doesn't instruct NVDA to change language:
        The add-on will only interpret the language if there are no instructions to change the language in the text. In the example above, it will switch to an english voice.
    * never interpret (NVDA's default behavior):
        Self explanatory.
* Languages to interpret:
    This is a list of the languages to interpret. If the add-on interprets a text as a language that isn't selected in this list, no auto language switching is done based on the interpretation. No languages are selected by default.

## Change log.
### v1.1
* Added compatibillity with NVDA 2025.
* Fixed a bug that caused the add-on to play error sounds when exiting NVDA.
* Made it so no language interpretation is performed (as it is verry slo) if the user has auto language switching turned off.
* Russian translation has been added, thanks to Kostenkov-2021
### v1.0

Initial release