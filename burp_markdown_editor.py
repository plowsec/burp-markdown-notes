from burp import IBurpExtender, ITab
from javax.swing.event import DocumentListener
from javax.swing import (JPanel, JSplitPane, JTextArea, JScrollPane,
                        JEditorPane, JToolBar, JButton, BorderFactory)
from java.awt import BorderLayout, Font, Color, Dimension


class DocumentListener(DocumentListener):
    def __init__(self):
        self._extender = None

    def set_extender(self, extender):
        self._extender = extender

    def changedUpdate(self, e):
        self._textChanged()

    def removeUpdate(self, e):
        self._textChanged()

    def insertUpdate(self, e):
        self._textChanged()

    def _textChanged(self):
        if self._extender:
            self._extender._updatePreview()
            self._extender._saveNotes()

class BurpExtender(IBurpExtender, ITab):


    def registerExtenderCallbacks(self, callbacks):
        self._callbacks = callbacks
        callbacks.setExtensionName("Markdown Notes")
        self._setupUI()
        callbacks.customizeUiComponent(self._splitpane)
        callbacks.addSuiteTab(self)

        # register a listener for changes in the editor
        listener = DocumentListener()
        listener.set_extender(self)
        self._editor.getDocument().addDocumentListener(listener)

        self._loadNotes()

    def _setupUI(self):
        self._mainPanel = JPanel(BorderLayout())

        # split pane for editor and preview
        self._splitpane = JSplitPane(JSplitPane.HORIZONTAL_SPLIT)
        self._splitpane.setBorder(None)

        # Create left panel for editor with toolbar
        leftPanel = JPanel(BorderLayout(0, 0))
        leftPanel.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 5))

        # Create right panel for preview
        rightPanel = JPanel(BorderLayout(0, 0))
        rightPanel.setBorder(BorderFactory.createEmptyBorder(40, 10, 10, 10))

        # create toolbar with markdown shortcuts
        toolbar = self._createToolbar()
        toolbar.setPreferredSize(Dimension(200, 30))
        leftPanel.add(toolbar, BorderLayout.NORTH)

        # markdown editor
        self._editor = JTextArea()
        self._editor.setFont(Font("Monospaced", Font.PLAIN, 12))
        self._editor.setBorder(BorderFactory.createEmptyBorder(5, 5, 5, 5))
        scrollEditor = JScrollPane(self._editor)

        editorPanel = JPanel(BorderLayout())
        editorPanel.add(scrollEditor, BorderLayout.CENTER)
        leftPanel.add(editorPanel, BorderLayout.CENTER)

        self._preview = JEditorPane("text/html", "")
        self._preview.setEditable(False)
        self._preview.setBorder(BorderFactory.createEmptyBorder(5, 5, 5, 5))  # Add inner padding
        scrollPreview = JScrollPane(self._preview)
        rightPanel.add(scrollPreview, BorderLayout.CENTER)

        self._splitpane.setLeftComponent(leftPanel)
        self._splitpane.setRightComponent(rightPanel)

        self._splitpane.setResizeWeight(0.5)  # Equal sizing

        self._mainPanel.add(self._splitpane, BorderLayout.CENTER)

    def _createToolbar(self):
        toolbar = JToolBar()
        toolbar.setFloatable(False)
        toolbar.setBorder(BorderFactory.createEmptyBorder(0, 0, 5, 0))
        toolbar.setBackground(Color(240, 240, 240))

        buttons = [
            ("Bold", "**Bold**"),
            ("Italic", "*Italic*"),
            ("Code", "`Code`"),
            ("Link", "[Link](url)"),
            ("List", "- List item"),
            ("Header", "# Header"),
        ]

        for name, text in buttons:
            button = JButton(name)
            button.addActionListener(lambda event, t=text: self._insertText(t))
            # Style the button
            button.setFocusPainted(False)
            button.setBackground(Color(250, 250, 250))
            toolbar.add(button)
            toolbar.addSeparator(Dimension(5, 0))

        return toolbar

    def _insertText(self, text):
        pos = self._editor.getCaretPosition()
        self._editor.insert(text, pos)
        self._editor.requestFocus()

    def getTabCaption(self):
        return "Notes"

    def getUiComponent(self):
        return self._splitpane

    def _loadNotes(self):
        # try to load previously saved notes
        try:
            notes = self._callbacks.loadExtensionSetting("saved_notes")
            if notes:
                self._editor.setText(notes)
                self._updatePreview()
        except:
            pass

    def _saveNotes(self):
        # save current notes
        self._callbacks.saveExtensionSetting("saved_notes", self._editor.getText())

    def _updatePreview(self):
        text = self._editor.getText()
        html = self._markdown_to_html(text)
        styled_html = """
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    code { background-color: #f0f0f0; padding: 2px 4px; border-radius: 4px; }
                    pre { background-color: #f0f0f0; padding: 10px; border-radius: 4px; }
                    blockquote { border-left: 4px solid #ccc; margin-left: 0; padding-left: 16px; }
                </style>
            </head>
            <body>
                %s
            </body>
            </html>
        """ % html

        self._preview.setText(styled_html)
        self._preview.setCaretPosition(0)

    def _markdown_to_html(self, text):
        """Simple markdown to HTML converter"""
        lines = text.split("\n")
        html_lines = []
        in_code_block = False
        in_list = False

        for line in lines:
            # Code blocks
            if line.startswith("```"):
                if in_code_block:
                    html_lines.append("</pre>")
                    in_code_block = False
                else:
                    html_lines.append("<pre><code>")
                    in_code_block = True
                continue

            if in_code_block:
                html_lines.append(self._escape_html(line))
                continue

            # Headers
            if line.startswith("# "):
                html_lines.append("<h1>%s</h1>" % self._process_inline(line[2:]))
            elif line.startswith("## "):
                html_lines.append("<h2>%s</h2>" % self._process_inline(line[3:]))
            elif line.startswith("### "):
                html_lines.append("<h3>%s</h3>" % self._process_inline(line[4:]))

            # Lists
            elif line.startswith("- "):
                if not in_list:
                    html_lines.append("<ul>")
                    in_list = True
                html_lines.append("<li>%s</li>" % self._process_inline(line[2:]))
            elif in_list and not line.startswith("- "):
                html_lines.append("</ul>")
                in_list = False

            # Blockquotes
            elif line.startswith(">"):
                html_lines.append("<blockquote>%s</blockquote>" % self._process_inline(line[1:]))

            # Horizontal rule
            elif line.startswith("---"):
                html_lines.append("<hr>")

            # Regular paragraph
            elif line.strip():
                html_lines.append("<p>%s</p>" % self._process_inline(line))

            # Blank line
            else:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append("<br>")

        return "\n".join(html_lines)

    def _process_inline(self, text):
        """Process inline markdown elements"""
        # Code
        text = self._replace_between(text, "`", "`", lambda x: "<code>%s</code>" % self._escape_html(x))

        # Bold
        text = self._replace_between(text, "**", "**", lambda x: "<strong>%s</strong>" % x)
        text = self._replace_between(text, "__", "__", lambda x: "<strong>%s</strong>" % x)

        # Italic
        text = self._replace_between(text, "*", "*", lambda x: "<em>%s</em>" % x)
        text = self._replace_between(text, "_", "_", lambda x: "<em>%s</em>" % x)

        # Links
        while "[" in text and "](" in text and ")" in text:
            start = text.find("[")
            mid = text.find("](", start)
            end = text.find(")", mid)
            if start == -1 or mid == -1 or end == -1:
                break
            link_text = text[start+1:mid]
            url = text[mid+2:end]
            text = text[:start] + '<a href="%s">%s</a>' % (url, link_text) + text[end+1:]

        return text

    def _replace_between(self, text, start_marker, end_marker, replacer):
        """Replace text between markers with the result of replacer function"""
        result = []
        while start_marker in text:
            start = text.find(start_marker)
            if start == -1:
                break
            end = text.find(end_marker, start + len(start_marker))
            if end == -1:
                break

            result.append(text[:start])
            content = text[start + len(start_marker):end]
            result.append(replacer(content))
            text = text[end + len(end_marker):]
        result.append(text)
        return "".join(result)

    def _escape_html(self, text):
        """Escape HTML special characters"""
        return (text.replace("&", "&amp;")
                   .replace("<", "&lt;")
                   .replace(">", "&gt;")
                   .replace("\"", "&quot;")
                   .replace("'", "&#39;"))