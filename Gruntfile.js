module.exports = function(grunt) {
    grunt.initConfig({
        pkg: grunt.file.readJSON('package.json'),

        jade: {
          compile: {
            options: {
              data: {
                debug: false
              },
              pretty: false,
            },
            files: [{
              expand: true,
              cwd: 'blender-today/src/jade',
              src: [ '**/*.jade' ],
              dest: 'blender-today/application/templates',
              ext: '.html'
            }]
          }
        },


        sass: {
            dist: {
                options: {
                    style: 'compressed'
                },
                files: {
                    'blender-today/application/static/css/main.css': 'blender-today/src/sass/main.sass'
                }
            }
        },

        uglify: {
            all_src : {
              src : 'blender-today/application/static/js/uglify/*.js',
              dest : 'blender-today/application/static/js/theuniverse.min.js'
            }
        },

        autoprefixer: {
            no_dest: { src: 'blender-today/application/static/css/main.css' }
        },

        watch: {
            files: ['blender-today/src/sass/main.sass'],
            js:  { files: 'blender-today/application/static/js/uglify/*.js', tasks: [ 'uglify' ] },
            tasks: ['sass', 'autoprefixer', 'uglify', 'jade'],
            jade: {
              files: 'blender-today/src/jade/**/*.jade',
              tasks: [ 'jade' ]
            },
        }
    });

    grunt.loadNpmTasks('grunt-contrib-sass');
    grunt.loadNpmTasks('grunt-contrib-watch');
    grunt.loadNpmTasks('grunt-contrib-uglify');
    grunt.loadNpmTasks('grunt-contrib-jade');
    grunt.loadNpmTasks('grunt-autoprefixer');

    grunt.registerTask('default', ['sass', 'autoprefixer', 'uglify']);
};
