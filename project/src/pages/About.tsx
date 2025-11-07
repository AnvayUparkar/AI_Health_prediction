import React from 'react';
import { Users, Target, Heart, Award } from 'lucide-react';

const About = () => {
  const teamMembers = [
    { name: 'Goopesh Sheth', role: 'AI/ML Engineer' },
    { name: 'Shravani Shewale', role: 'Data Scientist' },
    { name: 'Anay Uparkar', role: 'Full Stack Developer' },
    { name: 'Nishidh Vora', role: 'Product Designer' },
  ];

  const values = [
    {
      icon: <Target className="h-6 w-6" />,
      title: "Precision",
      description: "Using advanced AI to provide accurate health risk assessments"
    },
    {
      icon: <Heart className="h-6 w-6" />,
      title: "Care",
      description: "Putting user health and wellbeing at the center of everything we do"
    },
    {
      icon: <Award className="h-6 w-6" />,
      title: "Excellence",
      description: "Committed to delivering high-quality, reliable health technology"
    }
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      {/* Hero Section */}
      <div className="text-center mb-16">
        <div className="flex justify-center mb-6">
          <div className="p-4 bg-health-primary rounded-2xl">
            <Users className="h-12 w-12 text-white" />
          </div>
        </div>
        <h1 className="text-4xl md:text-5xl font-bold text-health-text mb-6">Our Mission & Team</h1>
        <p className="text-xl text-gray-600 max-w-3xl mx-auto leading-relaxed">
          We're a passionate team of technologists and healthcare enthusiasts dedicated to making 
          health awareness accessible through cutting-edge AI technology.
        </p>
      </div>

      {/* Mission Section */}
      <div className="bg-white rounded-2xl shadow-lg p-8 md:p-12 mb-16">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div>
            <h2 className="text-3xl font-bold text-health-text mb-6">Our Aim</h2>
            <p className="text-gray-600 leading-relaxed mb-6">
              Our aim is to make preliminary health assessment accessible and easy to understand for everyone. 
              We believe that technology can empower individuals to be more aware of their health and take 
              proactive steps towards prevention and early detection.
            </p>
            <p className="text-gray-600 leading-relaxed">
              By democratizing access to AI-powered health insights, we're helping people make informed 
              decisions about their wellbeing and encouraging them to seek professional medical guidance 
              when needed.
            </p>
          </div>
          <div className="bg-gradient-to-br from-blue-50 to-indigo-100 rounded-xl p-8">
            <div className="space-y-6">
              {values.map((value, index) => (
                <div key={index} className="flex items-start space-x-4">
                  <div className="p-2 bg-white rounded-lg shadow-sm">
                    <div className="text-health-primary">
                      {value.icon}
                    </div>
                  </div>
                  <div>
                    <h3 className="font-semibold text-health-text mb-1">{value.title}</h3>
                    <p className="text-sm text-gray-600">{value.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Team Section */}
      <div className="text-center mb-12">
        <h2 className="text-3xl font-bold text-health-text mb-4">Meet the Team</h2>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Our diverse team combines expertise in artificial intelligence, healthcare, and user experience 
          to create powerful and accessible health prediction tools.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mb-16">
        {teamMembers.map((member, index) => (
          <div key={index} className="bg-white rounded-xl shadow-lg p-6 text-center hover:shadow-xl transition-shadow duration-300">
            <div className="w-20 h-20 bg-gradient-to-br from-health-primary to-blue-600 rounded-full mx-auto mb-4 flex items-center justify-center">
              <span className="text-white text-2xl font-bold">
                {member.name.split(' ').map(n => n[0]).join('')}
              </span>
            </div>
            <h3 className="text-xl font-bold text-health-text mb-2">{member.name}</h3>
            <p className="text-health-primary font-medium text-sm">{member.role}</p>
          </div>
        ))}
      </div>

      {/* Vision Statement */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-2xl p-8 md:p-12 text-white text-center">
        <h2 className="text-3xl font-bold mb-6">Our Vision for the Future</h2>
        <p className="text-xl leading-relaxed max-w-4xl mx-auto opacity-95">
          We envision a world where everyone has access to personalized health insights that help them 
          live healthier, more informed lives. Through continuous innovation in AI and healthcare technology, 
          we're working towards a future where preventive care is the norm, not the exception.
        </p>
      </div>
    </div>
  );
};

export default About;