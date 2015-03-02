module.exports = function(grunt) {
    grunt.initConfig({
        pkg: grunt.file.readJSON('package.json'),

        sass: {
            dist: {
                options: {
                    style: 'compressed'
                },
                files: {
                    'blender-today/application/static/css/main.css': 'blender-today/application/static/sass/main.sass'
                }
            }
        },

        uglify: {
            all_src : {
              src : 'blender-today/application/static/js/uglify/*.js',
              dest : 'blender-today/application/static/js/theuniverse.all.min.js'
            }
        },

        autoprefixer: {
            no_dest: { src: 'blender-today/application/static/css/main.css' }
        },

        watch: {
            files: ['blender-today/application/static/sass/main.sass'],
            js:  { files: 'blender-today/application/static/js/uglify/*.js', tasks: [ 'uglify' ] },
            tasks: ['sass', 'autoprefixer'],
        }
    });

    grunt.loadNpmTasks('grunt-contrib-sass');
    grunt.loadNpmTasks('grunt-contrib-watch');
    grunt.loadNpmTasks('grunt-contrib-uglify');
    grunt.loadNpmTasks('grunt-autoprefixer');

    grunt.registerTask('default', ['sass', 'autoprefixer', 'uglify']);
};
