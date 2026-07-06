import { useCallback, useRef } from 'react';
import api from '../utils/api';

/**
 * Hook that registers a Monaco completion provider for Tab autocomplete.
 * Calls the backend inline suggestions API and presents results as completions.
 */
export function useTabAutocomplete(language) {
  const lastRequestRef = useRef(0);

  const registerProvider = useCallback((editor, monaco) => {
    const provider = monaco.languages.registerCompletionItemProvider(language?.id || 'python', {
      triggerCharacters: ['.', ' ', '(', ',', '\n'],
      provideCompletionItems: async (model, position) => {
        const now = Date.now();
        if (now - lastRequestRef.current < 300) {
          return { suggestions: [] };
        }
        lastRequestRef.current = now;

        const code = model.getValue();
        const line = position.lineNumber;
        const wordInfo = model.getWordUntilPosition(position);
        const range = {
          startLineNumber: line,
          startColumn: wordInfo.startColumn,
          endLineNumber: line,
          endColumn: wordInfo.endColumn,
        };

        try {
          const res = await api.post('/api/suggestions/', {
            code,
            line,
          });

          const suggestions = (res.data.suggestions || []).map((s) => {
            let insertText = s.suggestion || '';
            let kind = monaco.languages.CompletionItemKind.Issue;

            if (s.type === 'unused_import') {
              kind = monaco.languages.CompletionItemKind.Event;
              insertText = '';
            } else if (s.type === 'missing_docstring') {
              kind = monaco.languages.CompletionItemKind.Snippet;
            } else if (s.type === 'bad_naming') {
              kind = monaco.languages.CompletionItemKind.Variable;
            } else if (s.type === 'long_line') {
              kind = monaco.languages.CompletionItemKind.Struct;
            } else if (s.type === 'simple_bool') {
              kind = monaco.languages.CompletionItemKind.Enum;
            }

            return {
              label: `${s.type}: ${s.message}`,
              kind,
              documentation: `Current: ${s.current}\nSuggested: ${insertText}`,
              insertText: insertText || s.current,
              range,
              sortText: `0-${s.severity === 'warning' ? '0' : '1'}-${s.line}`,
              filterText: s.message,
            };
          });

          return { suggestions };
        } catch {
          return { suggestions: [] };
        }
      },
    });

    return provider;
  }, [language?.id]);

  return { registerProvider };
}
