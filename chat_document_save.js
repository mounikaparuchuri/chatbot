/**
 * Shared silent document save for FMC chat interfaces.
 *
 * Per-page usage:
 *   <script src="chat_document_save.js"></script>
 *   const documentSave = ChatDocumentSave.create({
 *     documentTypeId: 'talent_interest_explorer',  // SAVE — this page's output
 *     sourceDocumentTypeId: 'energy_tracker',       // FETCH — prior page's output
 *     sourceDocumentLabel: 'Energy Tracker Results',
 *     userId, courseId,
 *     trigger: ChatDocumentSave.triggers.topTalentThemes()
 *   });
 *   // On start conversation:
 *   await documentSave.prepareAgentPayload(payload, starterText);
 *   function handleAgentResponse(data) {
 *     return documentSave.handleAgentResponse(data, extractN8nWebhookReply, addMessage, formatMissingWebhookReply);
 *   }
 */
(function (global) {
    'use strict';

    var DEFAULT_SAVE_WEBHOOK = 'https://n8n.paruchuri.net/webhook/3a2ede5a-1d84-45ff-8610-ea8a914f2fbe';
    var DEFAULT_FETCH_WEBHOOK = DEFAULT_SAVE_WEBHOOK;

    function extractDocumentFromFetchResponse(raw) {
        if (raw == null) return null;
        if (typeof raw === 'string') {
            var trimmed = raw.trim();
            return trimmed ? trimmed : null;
        }
        if (typeof raw !== 'object') return null;
        if (raw.document != null) return raw.document;
        if (raw.record && raw.record.document != null) return raw.record.document;
        if (Array.isArray(raw.records) && raw.records[0] && raw.records[0].document != null) {
            return raw.records[0].document;
        }
        if (raw.data != null && typeof raw.data === 'object' && !Array.isArray(raw.data)) {
            return extractDocumentFromFetchResponse(raw.data);
        }
        if (Object.keys(raw).length) return raw;
        return null;
    }

    function formatDocumentForChatInput(doc, label) {
        if (doc == null) return '';
        label = label || 'Loaded document';
        if (typeof doc === 'string') return '\n\n--- ' + label + ' ---\n' + doc;
        return '\n\n--- ' + label + ' ---\n' + JSON.stringify(doc, null, 2);
    }

    function gatherWebhookStrings(raw, depth, out) {
        depth = depth || 0;
        out = out || [];
        if (depth > 14 || raw == null) return out;
        if (typeof raw === 'string') {
            var t = raw.trim();
            if (t) out.push(t);
            return out;
        }
        if (Array.isArray(raw)) {
            for (var i = 0; i < raw.length; i++) gatherWebhookStrings(raw[i], depth + 1, out);
            return out;
        }
        if (typeof raw === 'object') {
            var keys = Object.keys(raw);
            for (var j = 0; j < keys.length; j++) gatherWebhookStrings(raw[keys[j]], depth + 1, out);
        }
        return out;
    }

    function normalizeSectionText(text) {
        return text
            .replace(/\*\*/g, '')
            .replace(/__/g, '')
            .replace(/#{1,6}\s+/g, '')
            .replace(/\r\n/g, '\n');
    }

    function hasPhrase(text, phraseRe) {
        if (!text || typeof text !== 'string') return false;
        return phraseRe.test(normalizeSectionText(text));
    }

    function findBestMatchingText(responseText, rawData, phraseRe) {
        var candidates = [];
        if (responseText && typeof responseText === 'string') candidates.push(responseText.trim());
        gatherWebhookStrings(rawData).forEach(function (s) {
            if (hasPhrase(s, phraseRe)) candidates.push(s);
        });
        var best = '';
        for (var i = 0; i < candidates.length; i++) {
            if (candidates[i].length > best.length) best = candidates[i];
        }
        return best || (typeof responseText === 'string' ? responseText.trim() : '');
    }

    function parseSectionAfterPhrase(text, phraseRe) {
        if (!text || typeof text !== 'string') return '';
        var normalized = normalizeSectionText(text);
        var match = phraseRe.exec(normalized);
        if (!match) return normalized.trim();

        var after = normalized.slice(match.index + match[0].length).replace(/^[\s:*\-#]+/, '').trim();
        if (after) return after;
        return normalized.trim();
    }

    function documentFromBulletedSection(block, fullText, listKey) {
        listKey = listKey || 'items';
        var items = [];
        var lines = (block || '').split('\n');
        for (var i = 0; i < lines.length; i++) {
            var line = lines[i].trim();
            if (!line) continue;
            var bullet = line.match(/^\s*(?:\d+[\.\)]\s*|[-*•]\s+)(.+)$/);
            if (bullet) {
                items.push(bullet[1].trim());
                continue;
            }
            if (!/^#{1,6}\s/.test(line)) items.push(line);
        }
        var doc = {};
        doc[listKey] = items.length ? items : [block.trim()];
        doc.raw_section = block.trim();
        if (fullText && typeof fullText === 'string') doc.summary_message = fullText.trim();
        return doc;
    }

    function createSectionPhraseTrigger(options) {
        options = options || {};
        var phraseRe = options.phrase instanceof RegExp ? options.phrase : new RegExp(options.phrase, 'i');
        var listKey = options.listKey || 'items';
        var buildDocument = options.buildDocument;

        return {
            detect: function (responseText, rawData) {
                var text = findBestMatchingText(responseText, rawData, phraseRe);
                if (!text || !hasPhrase(text, phraseRe)) return null;
                var block = parseSectionAfterPhrase(text, phraseRe);
                return {
                    displayMessage: text,
                    document: buildDocument
                        ? buildDocument(text, block)
                        : documentFromBulletedSection(block, text, listKey)
                };
            }
        };
    }

    function createDocumentSave(config) {
        config = config || {};
        var saveWebhookUrl = config.saveWebhookUrl || DEFAULT_SAVE_WEBHOOK;
        var fetchWebhookUrl = config.fetchWebhookUrl || config.saveWebhookUrl || DEFAULT_FETCH_WEBHOOK;
        var documentTypeId = config.documentTypeId || 'chat_summary';
        var sourceDocumentTypeId = config.sourceDocumentTypeId || null;
        var sourceDocumentLabel = config.sourceDocumentLabel || 'Loaded document';
        var userId = config.userId || '';
        var courseId = config.courseId || '';
        var trigger = config.trigger;
        var cachedSourceDocument = null;
        var sourceDocumentFetched = false;
        var sourceDocumentInjected = false;

        if (!trigger || typeof trigger.detect !== 'function') {
            throw new Error('ChatDocumentSave.create requires config.trigger with detect()');
        }

        async function fetchSourceDocument() {
            if (!sourceDocumentTypeId) return null;
            if (sourceDocumentFetched) return cachedSourceDocument;
            sourceDocumentFetched = true;
            try {
                var res = await fetch(fetchWebhookUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: userId,
                        course_id: courseId,
                        document_type_id: sourceDocumentTypeId
                    })
                });
                if (!res.ok) throw new Error('HTTP error! status: ' + res.status);
                var data = await res.json().catch(function () { return null; });
                cachedSourceDocument = extractDocumentFromFetchResponse(data);
            } catch (err) {
                console.error('Fetch source document error:', err);
                cachedSourceDocument = null;
            }
            return cachedSourceDocument;
        }

        function appendSourceDocumentFields(payload, chatInput) {
            if (!sourceDocumentTypeId || cachedSourceDocument == null || sourceDocumentInjected) {
                return chatInput;
            }
            sourceDocumentInjected = true;
            payload.sourceDocumentTypeId = sourceDocumentTypeId;
            payload.sourceDocument = cachedSourceDocument;
            return chatInput + formatDocumentForChatInput(cachedSourceDocument, sourceDocumentLabel);
        }

        async function prepareAgentPayload(basePayload, chatInput) {
            if (sourceDocumentTypeId && !sourceDocumentFetched) {
                await fetchSourceDocument();
            }
            basePayload.chatInput = appendSourceDocumentFields(basePayload, chatInput || '');
            return basePayload;
        }

        function resetSourceDocumentCache() {
            cachedSourceDocument = null;
            sourceDocumentFetched = false;
            sourceDocumentInjected = false;
        }

        async function saveDocument(documentPayload) {
            if (!documentPayload) return;
            try {
                var res = await fetch(saveWebhookUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: userId,
                        course_id: courseId,
                        document_type_id: documentTypeId,
                        document: documentPayload
                    })
                });
                if (!res.ok) throw new Error('HTTP error! status: ' + res.status);
                await res.json().catch(function () { return {}; });
            } catch (err) {
                console.error('Save error:', err);
            }
        }

        function handleAgentResponse(data, extractReply, addMessage, formatMissing) {
            var responseText = extractReply(data) || '';
            var completion = null;
            try {
                completion = trigger.detect(responseText, data);
            } catch (err) {
                console.error('Save trigger detection error:', err);
            }

            if (completion) {
                addMessage(completion.displayMessage, false);
                saveDocument(completion.document);
                return true;
            }

            addMessage(responseText || formatMissing(data), false);
            return false;
        }

        return {
            documentTypeId: documentTypeId,
            sourceDocumentTypeId: sourceDocumentTypeId,
            detectCompletion: function (responseText, rawData) {
                return trigger.detect(responseText, rawData);
            },
            fetchSourceDocument: fetchSourceDocument,
            prepareAgentPayload: prepareAgentPayload,
            resetSourceDocumentCache: resetSourceDocumentCache,
            saveDocument: saveDocument,
            handleAgentResponse: handleAgentResponse
        };
    }

    function resolveDocumentTypeId(pageDefault) {
        var urlParams = new URLSearchParams(global.location && global.location.search || '');
        return urlParams.get('document_type_id')
            || pageDefault
            || (global.PLATFORM_DOC_TYPE)
            || 'chat_summary';
    }

    function resolveSourceDocumentTypeId(pageDefault) {
        var urlParams = new URLSearchParams(global.location && global.location.search || '');
        return urlParams.get('source_document_type_id')
            || urlParams.get('fetch_document_type_id')
            || pageDefault
            || (global.PLATFORM_SOURCE_DOC_TYPE)
            || null;
    }

    function resolveUserContext() {
        var urlParams = new URLSearchParams(global.location && global.location.search || '');
        return {
            userId: urlParams.get('user_id') || global.PLATFORM_USER_ID || '',
            courseId: urlParams.get('course_id') || global.PLATFORM_COURSE_ID || ''
        };
    }

    global.ChatDocumentSave = {
        DEFAULT_SAVE_WEBHOOK: DEFAULT_SAVE_WEBHOOK,
        DEFAULT_FETCH_WEBHOOK: DEFAULT_FETCH_WEBHOOK,
        create: createDocumentSave,
        resolveDocumentTypeId: resolveDocumentTypeId,
        resolveSourceDocumentTypeId: resolveSourceDocumentTypeId,
        resolveUserContext: resolveUserContext,
        formatDocumentForChatInput: formatDocumentForChatInput,
        triggers: {
            /** Talent Interest Explorer — "Top Talent Themes" */
            topTalentThemes: function () {
                return createSectionPhraseTrigger({
                    phrase: /(?:your\s+)?top\s+\d*\s*talent\s+themes?/i,
                    listKey: 'top_talent_themes'
                });
            },
            /** Generic: pass your own phrase regex and optional list key */
            sectionPhrase: createSectionPhraseTrigger
        }
    };
})(typeof window !== 'undefined' ? window : this);
