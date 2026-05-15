# coding: utf-8
# Copyright 2025 Emil-18
# An add-on that detects languages based on the spoken text itself
# This add-on is licensed under the same license as NVDA. See the copying.txt file for more information

import addonHandler
addonHandler.initTranslation()
import os
import sys

# Vendored `six` lives next to this __init__.py because langdetect does an
# absolute `import six`. Put the add-on dir on sys.path so that import resolves,
# then leave it there for the lifetime of the process — once `six` is in
# sys.modules it stays cached, but langdetect submodules are imported lazily
# in some code paths, so removing the path entry is unsafe.
_addonDir = os.path.dirname(__file__)
if _addonDir not in sys.path:
	sys.path.insert(0, _addonDir)

import config
import globalPluginHandler
import gui
from gui.settingsDialogs import SettingsPanel
import languageHandler
import wx
from logHandler import log
from speech.commands import LangChangeCommand
from speech.extensions import filter_speechSequence
from . import langdetect
from . import lingua

profilePath = os.path.join(os.path.dirname(__file__), "langdetect", "profiles")
languages = os.listdir(profilePath)
detector = None

# Lingua v2 exposes Language as a PyO3 type, not a stdlib Enum, so it's not directly iterable.
# Use Language.all() and sort by name for a stable order across runs (config keys, UI indices).
LINGUA_LANGUAGES = sorted(lingua.Language.all(), key=lambda l: l.name)

confspec = {
	"languageDetection": "integer(default=1)",
	"model": "integer(default=0)",
	"detectMultipleLanguages": "boolean(default=True)",
	"minWordsForLanguageChange": "integer(default=3, min=1, max=50)",
}

for i in languages:
	confspec.update({i: "boolean(default=False)"})
for i in LINGUA_LANGUAGES:
	confspec.update({"lingua_" + i.iso_code_639_1.name: "boolean(default=False)"})
config.conf.spec["enhancedLanguageDetection"] = confspec


def updateDetector():
	"""Rebuild the lingua detector from the user's language selections.

	Lingua v2 requires at least two languages and uses varargs constructors.
	"""
	global detector
	selected = []
	for i in LINGUA_LANGUAGES:
		if config.conf["enhancedLanguageDetection"]["lingua_" + i.iso_code_639_1.name]:
			selected.append(i)
	if len(selected) >= 2:
		try:
			detector = lingua.LanguageDetectorBuilder.from_languages(*selected).build()
		except Exception as e:
			log.error(f"enhancedLanguageDetection: failed to build lingua detector: {e}")
			detector = None
	else:
		# Lingua v2 needs >=2 languages; with 0 or 1, leave detection disabled.
		detector = None
	return detector


class EnhancedLanguageDetectionSettingsPanel(SettingsPanel):
	# Translators: The title for the settings panel
	title = _("Enhanced Language Detection")

	def handleModelChange(self, evt):
		self.linguaLanguages.Enable(evt.GetSelection() == 0)
		self.languages.Enable(evt.GetSelection())
		self.multiple.Enable(evt.GetSelection() == 0)

	def makeSettings(self, settingsSizer):
		settings = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		modelComboBoxValues = [
			# Translators: An option in a combo box
			_("lingua (recommended)"),
			"langdetect",
		]
		# Translators: the label for a combo box
		label = _("language detection library")
		self.modelComboBox = settings.addLabeledControl(label, wx.Choice, choices=modelComboBoxValues)
		self.modelComboBox.SetSelection(config.conf["enhancedLanguageDetection"]["model"])
		self.modelComboBox.Bind(wx.EVT_CHOICE, self.handleModelChange)
		comboBoxValues = [
			# Translators: An option in a combo box
			_("always interpret"),
			# Translators: An option in a combo box
			_("only interpret if the text doesn't instruct NVDA to change language"),
			# Translators: An option in a combo box
			_("never interpret (NVDA's default behavior)"),
		]
		# Translators: The label for a combo box
		label = _("Language interpretation:")
		self.languageDetection = settings.addLabeledControl(label, wx.Choice, choices=comboBoxValues)
		self.languageDetection.SetSelection(config.conf["enhancedLanguageDetection"]["languageDetection"])
		# Translators: The label for a check box
		label = _("Detect multiple languages in the same text")
		self.multiple = settings.addItem(wx.CheckBox(self, label=label))
		self.multiple.SetValue(config.conf["enhancedLanguageDetection"]["detectMultipleLanguages"])
		self.multiple.Enable(config.conf["enhancedLanguageDetection"]["model"] == 0)
		# Translators: The label for a numeric input controlling the minimum number of words before a language switch is applied.
		label = _("Minimum number of words required to switch language")
		self.minWords = settings.addLabeledControl(
			label,
			wx.SpinCtrl,
			min=1,
			max=50,
			initial=config.conf["enhancedLanguageDetection"]["minWordsForLanguageChange"],
		)
		# Translators: The label for a checkable list box
		label = _("Languages to interpret")
		choices = []
		for i in languages:
			description = languageHandler.getLanguageDescription(i)
			if description:
				choices.append(description)
			else:
				choices.append(i)
		self.languages = settings.addLabeledControl(label, gui.nvdaControls.CustomCheckListBox, choices=choices)
		self.languages.SetSelection(0)
		checked = []
		for i in range(len(languages)):
			if config.conf["enhancedLanguageDetection"][languages[i]]:
				checked.append(i)
		self.languages.SetCheckedItems(checked)
		choices = []
		for i in LINGUA_LANGUAGES:
			description = languageHandler.getLanguageDescription(i.iso_code_639_1.name)
			if description:
				choices.append(description)
			else:
				choices.append(i.iso_code_639_1.name)
		self.linguaLanguages = settings.addLabeledControl(label, gui.nvdaControls.CustomCheckListBox, choices=choices)
		self.linguaLanguages.SetSelection(0)
		checked = []
		for idx, lang in enumerate(LINGUA_LANGUAGES):
			if config.conf["enhancedLanguageDetection"]["lingua_" + lang.iso_code_639_1.name]:
				checked.append(idx)
		self.linguaLanguages.SetCheckedItems(checked)
		self.languages.Enable(config.conf["enhancedLanguageDetection"]["model"])
		self.linguaLanguages.Enable(config.conf["enhancedLanguageDetection"]["model"] == 0)

	def onSave(self):
		config.conf["enhancedLanguageDetection"]["languageDetection"] = self.languageDetection.GetSelection()
		config.conf["enhancedLanguageDetection"]["model"] = self.modelComboBox.GetSelection()
		config.conf["enhancedLanguageDetection"]["detectMultipleLanguages"] = self.multiple.GetValue()
		config.conf["enhancedLanguageDetection"]["minWordsForLanguageChange"] = self.minWords.GetValue()
		checked = self.languages.GetCheckedItems()
		for i in range(len(languages)):
			config.conf["enhancedLanguageDetection"][languages[i]] = i in checked
		checked = self.linguaLanguages.GetCheckedItems()
		for idx, lang in enumerate(LINGUA_LANGUAGES):
			config.conf["enhancedLanguageDetection"]["lingua_" + lang.iso_code_639_1.name] = idx in checked
		updateDetector()


def detectLanguage(text):
	try:
		langs = langdetect.detect_langs(text)
	except Exception:
		return
	if not langs:
		return
	for language in langs:
		if config.conf["enhancedLanguageDetection"][language.lang]:
			return language.lang


def detectLanguageWithLingua(text):
	if detector is None:
		return
	try:
		lang = detector.detect_language_of(text)
	except Exception:
		return
	if not lang:
		return
	return lang.iso_code_639_1.name


def detectMultipleLanguages(text, minWords):
	"""Split text into per-language segments, suppressing language changes for runs shorter than minWords."""
	if detector is None:
		return [text]
	try:
		detected = detector.detect_multiple_languages_of(text)
	except Exception:
		return [text]
	if not detected:
		return [text]
	sequence = []
	for result in detected:
		segment = text[result.start_index:result.end_index]
		# Lingua v2 exposes word_count on each DetectionResult; if a segment is too short,
		# don't emit a language change — let it inherit the surrounding voice.
		if getattr(result, "word_count", 0) >= minWords:
			sequence.append(LangChangeCommand(result.language.iso_code_639_1.name.lower()))
		sequence.append(segment)
	return sequence


def speechSequenceFilter(speechSequence, *args, **kwargs):
	conf = config.conf["enhancedLanguageDetection"]
	if conf["languageDetection"] == 2 or not config.conf["speech"]["autoLanguageSwitching"]:
		return speechSequence
	minWords = conf["minWordsForLanguageChange"]
	newSequence = []
	shouldInterpret = True
	# Track the most recent upstream LangChangeCommand. In always-interpret
	# mode we strip these from the output, but we re-emit the last one before
	# any below-threshold text so short tokens (single characters, symbol
	# names like "Punkt") still come out in the document's intended language.
	# Without this, character-by-character navigation through non-English
	# text plays the localized symbol names in the default voice.
	lastUpstreamLang = None
	for i in speechSequence:
		if isinstance(i, LangChangeCommand):
			lastUpstreamLang = i
			if conf["languageDetection"] == 0:
				# Always-interpret mode strips upstream language commands.
				continue
			shouldInterpret = not i.lang
		if isinstance(i, str):
			if shouldInterpret:
				# Don't run detection on text below the word threshold — too short to identify reliably,
				# and switching voice mid-utterance for one or two words causes audible artifacting.
				if len(i.split()) < minWords:
					if conf["languageDetection"] == 0 and lastUpstreamLang is not None:
						# Restore the upstream language so localized symbol
						# names play in the right voice during letter nav.
						newSequence.append(lastUpstreamLang)
					newSequence.append(i)
					continue
				if conf["model"] == 0 and conf["detectMultipleLanguages"]:
					newSequence.extend(detectMultipleLanguages(i, minWords))
					continue
				language = detectLanguage(i) if conf["model"] != 0 else detectLanguageWithLingua(i)
				if isinstance(language, str):
					language = language.lower()
				newSequence.append(LangChangeCommand(language))
			else:
				newSequence.append(i)
				continue
		newSequence.append(i)
	return newSequence


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(EnhancedLanguageDetectionSettingsPanel)
		updateDetector()
		filter_speechSequence.register(speechSequenceFilter)
		config.post_configProfileSwitch.register(updateDetector)

	def terminate(self, *args, **kwargs):
		config.post_configProfileSwitch.unregister(updateDetector)
		filter_speechSequence.unregister(speechSequenceFilter)
		gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(EnhancedLanguageDetectionSettingsPanel)
		super().terminate(*args, **kwargs)
