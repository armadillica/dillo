/**
 * @license Copyright (c) 2003-2015, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

CKEDITOR.editorConfig = function( config ) {
	// Define changes to default configuration here.
	// For complete reference see:
	// http://docs.ckeditor.com/#!/api/CKEDITOR.config

	CKEDITOR.plugins.addExternal( 'panel', '/static/js/ckeditor/panel/' );
	CKEDITOR.plugins.addExternal( 'panelbutton', '/static/js/ckeditor/panelbutton/' );
	CKEDITOR.plugins.addExternal( 'floatpanel', '/static/js/ckeditor/floatpanel/' );
	CKEDITOR.plugins.addExternal( 'listblock', '/static/js/ckeditor/listblock/' );
	CKEDITOR.plugins.addExternal( 'richcombo', '/static/js/ckeditor/richcombo/' );
	CKEDITOR.plugins.addExternal( 'format', '/static/js/ckeditor/format/' );
	CKEDITOR.plugins.addExternal( 'blockquote', '/static/js/ckeditor/blockquote/' );
	CKEDITOR.plugins.addExternal( 'colorbutton', '/static/js/ckeditor/colorbutton/' );

	// The toolbar groups arrangement, optimized for a single toolbar row.
	config.toolbarGroups = [
		{ name: 'document',	   groups: [ 'mode', 'document', 'doctools' ] },
		{ name: 'clipboard',   groups: [ 'clipboard', 'undo' ] },
		{ name: 'editing',     groups: [ 'find', 'selection', 'spellchecker' ] },
		{ name: 'forms' },
		{ name: 'basicstyles', groups: [ 'basicstyles', 'cleanup' ] },
		{ name: 'paragraph',   groups: [ 'list', 'indent', 'blocks', 'align', 'bidi' ] },
		{ name: 'links' },
		{ name: 'insert' },
		{ name: 'colors' },
		{ name: 'styles' },
		{ name: 'tools' },
		{ name: 'others' },
		{ name: 'about' }
	];

	config.extraPlugins = 'panel,panelbutton,floatpanel,listblock,richcombo,format,blockquote,colorbutton';
	config.removePlugins = 'elementspath';

	config.removeButtons = 'Cut,Copy,Paste,Undo,Redo,Anchor,Underline,Subscript,Superscript,About,NumberedList,Indent,Outdent,BGColor';

	config.resize_enabled = false;
	config.forcePasteAsPlainText = true;

	// Plugin Settings
	config.format_tags = 'p;h1;h2;pre';

	// Default colors for ColorButton plugin are fugly, set our own
	config.colorButton_colors = '444444,9D9D9D,FFFFFF,BE2633,E06F8B,493C2B,A46422,EB8931,F7E26B,2F484E,44891A,A3CE27,1B2632,005784,31A2F2,B2DCEF';

	// Dialog windows are simplified.
	config.removeDialogTabs = 'link:advanced';
};
