import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Container, 
  Typography, 
  Tabs, 
  Tab, 
  Paper, 
  Alert,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  Divider,
  Chip
} from '@mui/material';
import { useLocation } from 'react-router-dom';
import GraphVisualization from '../components/GraphVisualization';
import AdvancedGraphVisualization from '../components/AdvancedGraphVisualization';

const ResultsPage = () => {
  const location = useLocation();
  const [activeTab, setActiveTab] = useState(0);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [enhancedGraphData, setEnhancedGraphData] = useState({ nodes: [], links: [] });
  const [profileData, setProfileData] = useState(null);

  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  useEffect(() => {
    // Get profile data from location state
    if (location.state && location.state.profileData) {
      const data = location.state.profileData;
      
      // Check if the parsed data is sufficient for visualization
      const hasMinimumData = checkSufficientData(data);
      
      if (hasMinimumData) {
        setProfileData(data);
        transformDataToGraph(data);
      } else {
        // If insufficient data, enhance with sample data
        const enhancedData = enhanceWithSampleData(data);
        setProfileData(enhancedData);
        transformDataToGraph(enhancedData);
      }
    }
  }, [location.state]);
  
  // Check if the data has minimum required fields for visualization
  const checkSufficientData = (data) => {
    // Check if there's at least a name and one experience or one skill
    const hasName = data && data.name && data.name !== 'Profile';
    const hasExperience = data && data.experiences && Array.isArray(data.experiences) && data.experiences.length > 0;
    const hasSkills = data && data.skills && Array.isArray(data.skills) && data.skills.length > 0;
    
    return hasName && (hasExperience || hasSkills);
  };
  
  // Enhance minimal data with sample data
  const enhanceWithSampleData = (data) => {
    // Start with the original data or an empty object
    const enhancedData = { ...data } || {};
    
    // Keep the original name if available, otherwise use a placeholder
    enhancedData.name = data?.name || 'Your Profile';
    
    // Keep original headline or use placeholder
    enhancedData.headline = data?.headline || 'Professional with experience in technology';
    
    // Ensure there are experiences
    if (!enhancedData.experiences || !Array.isArray(enhancedData.experiences) || enhancedData.experiences.length === 0) {
      enhancedData.experiences = [
        {
          title: 'Technical Role',
          company: 'Technology Company',
          startDate: '2020-01',
          endDate: 'Present',
          description: 'Working on technical projects and solutions'
        },
        {
          title: 'Previous Role',
          company: 'Previous Company',
          startDate: '2018-01',
          endDate: '2019-12',
          description: 'Worked on various projects and initiatives'
        }
      ];
    }
    
    // Ensure there are skills
    if (!enhancedData.skills || !Array.isArray(enhancedData.skills) || enhancedData.skills.length === 0) {
      enhancedData.skills = [
        { name: 'Technical Skills', endorsements: 10 },
        { name: 'Problem Solving', endorsements: 8 },
        { name: 'Communication', endorsements: 12 }
      ];
    }
    
    // Ensure there is education
    if (!enhancedData.education || !Array.isArray(enhancedData.education) || enhancedData.education.length === 0) {
      enhancedData.education = [
        {
          school: 'University',
          degree: 'Degree',
          fieldOfStudy: 'Field of Study',
          startDate: '2014-09',
          endDate: '2018-05'
        }
      ];
    }
    
    return enhancedData;
  };

  // Transform the profile data into graph format
  const transformDataToGraph = (data) => {
    if (!data) return;

    try {
      // Initialize arrays for graph nodes and links
      const nodes = [];
      const links = [];
      
      // Create basic graph data (person and company connections)
      
      // Add person node
      const personId = `person-${data.id || '1'}`;
      nodes.push({
        id: personId,
        label: data.name || 'Profile',
        type: 'person',
        size: 20,
        description: data.headline || 'Professional'
      });
      
      // Add company nodes and links for work experiences
      if (data.experiences && Array.isArray(data.experiences)) {
        // Sort experiences by date if available
        const sortedExperiences = [...data.experiences].sort((a, b) => {
          if (a.startDate && b.startDate) {
            return new Date(b.startDate) - new Date(a.startDate);
          }
          return 0;
        });
        
        // Add all company nodes
        sortedExperiences.forEach((exp, index) => {
          const companyId = `company-${exp.company.replace(/\s+/g, '') || index}`;
          
          // Add company node if it doesn't exist
          if (!nodes.some(node => node.id === companyId)) {
            nodes.push({
              id: companyId,
              label: exp.company || `Company ${index + 1}`,
              type: 'company',
              size: 15,
              description: exp.description || ''
            });
          }
          
          // Add link from person to company
          links.push({
            source: personId,
            target: companyId,
            value: 2,
            label: exp.title || 'Worked at'
          });
        });
        
        // Add career progression links between companies
        for (let i = 0; i < sortedExperiences.length - 1; i++) {
          const currentCompanyId = `company-${sortedExperiences[i].company.replace(/\s+/g, '') || i}`;
          const nextCompanyId = `company-${sortedExperiences[i+1].company.replace(/\s+/g, '') || i+1}`;
          
          links.push({
            source: nextCompanyId,
            target: currentCompanyId,
            value: 1.5,
            label: 'Career Progression'
          });
        }
      }
      
      // Set basic graph data
      setGraphData({ nodes, links });
      
      // Create enhanced graph data (with skills, education, projects, certifications)
      const enhancedNodes = [...nodes];
      const enhancedLinks = [...links];
      
      // Add skill nodes and links
      if (data.skills && Array.isArray(data.skills)) {
        // Group skills by domain to create relationships between similar skills
        const skillDomains = {
          'engineering': ['Engineering Leadership', 'System Architecture', 'DevOps', 'Microservices'],
          'programming': ['Python', 'JavaScript', 'Java'],
          'ai': ['Artificial Intelligence', 'Machine Learning', 'Data Science'],
          'cloud': ['Cloud Infrastructure', 'AWS', 'Kubernetes'],
          'management': ['Agile Methodologies', 'Team Building', 'Product Development']
        };
        
        // Create a reverse lookup for skill domains
        const skillToDomain = {};
        Object.entries(skillDomains).forEach(([domain, skills]) => {
          skills.forEach(skill => {
            skillToDomain[skill] = domain;
          });
        });
        
        // Add skill nodes grouped by domain
        const skillIdMap = {};
        data.skills.forEach((skill, index) => {
          const skillId = `skill-${skill.name.replace(/\s+/g, '') || index}`;
          skillIdMap[skill.name] = skillId;
          
          // Add skill node
          enhancedNodes.push({
            id: skillId,
            label: skill.name || `Skill ${index + 1}`,
            type: 'skill',
            size: 8 + (skill.endorsements ? Math.min(skill.endorsements / 10, 4) : 0),
            description: `Endorsements: ${skill.endorsements || 0}`
          });
          
          // Add link from person to skill
          enhancedLinks.push({
            source: personId,
            target: skillId,
            value: 1,
            label: 'Has skill'
          });
          
          // Connect to companies where this skill was likely used
          data.experiences.forEach((exp, expIndex) => {
            // More relevant skills have higher chance of linking to companies
            const relevanceThreshold = 0.5 - (skill.endorsements ? skill.endorsements / 100 : 0);
            if (Math.random() > relevanceThreshold) {
              const companyId = `company-${exp.company.replace(/\s+/g, '') || expIndex}`;
              enhancedLinks.push({
                source: companyId,
                target: skillId,
                value: 0.7,
                label: 'Utilized'
              });
            }
          });
        });
        
        // Add links between related skills (within same domain)
        Object.values(skillDomains).forEach(domainSkills => {
          for (let i = 0; i < domainSkills.length; i++) {
            if (!skillIdMap[domainSkills[i]]) continue;
            
            for (let j = i + 1; j < domainSkills.length; j++) {
              if (!skillIdMap[domainSkills[j]]) continue;
              
              enhancedLinks.push({
                source: skillIdMap[domainSkills[i]],
                target: skillIdMap[domainSkills[j]],
                value: 0.5,
                label: 'Related'
              });
            }
          }
        });
      }
      
      // Add education nodes and links
      if (data.education && Array.isArray(data.education)) {
        data.education.forEach((edu, index) => {
          const eduId = `education-${edu.school.replace(/\s+/g, '') || index}`;
          
          // Add education node
          enhancedNodes.push({
            id: eduId,
            label: edu.school || `School ${index + 1}`,
            type: 'education',
            size: 12,
            description: edu.description || `${edu.degree || ''} ${edu.fieldOfStudy || ''}`
          });
          
          // Add link from person to education
          enhancedLinks.push({
            source: personId,
            target: eduId,
            value: 1.5,
            label: edu.degree || 'Studied at'
          });
          
          // Connect education to relevant skills
          const fieldToSkills = {
            'Computer Science': ['Python', 'Java', 'JavaScript', 'System Architecture', 'Artificial Intelligence', 'Machine Learning'],
            'Technology Management': ['Engineering Leadership', 'Team Building', 'Agile Methodologies', 'Product Development'],
            'Business Administration': ['Team Building', 'Product Development'],
            'Mathematics': ['Data Science', 'Machine Learning']
          };
          
          const relevantSkills = fieldToSkills[edu.fieldOfStudy] || [];
          relevantSkills.forEach(skillName => {
            const skillNodes = enhancedNodes.filter(node => 
              node.type === 'skill' && node.label === skillName
            );
            
            if (skillNodes.length > 0) {
              enhancedLinks.push({
                source: eduId,
                target: skillNodes[0].id,
                value: 0.7,
                label: 'Taught'
              });
            }
          });
        });
      }
      
      // Add certification nodes
      if (data.certifications && Array.isArray(data.certifications)) {
        data.certifications.forEach((cert, index) => {
          const certId = `cert-${cert.name.replace(/\s+/g, '') || index}`;
          
          // Add certification node
          enhancedNodes.push({
            id: certId,
            label: cert.name || `Certification ${index + 1}`,
            type: 'education',
            size: 10,
            description: `Issued by: ${cert.issuer || 'Unknown'}, Date: ${cert.date || 'Unknown'}`
          });
          
          // Link certification to person
          enhancedLinks.push({
            source: personId,
            target: certId,
            value: 1,
            label: 'Certified'
          });
          
          // Link certification to relevant skills
          const certToSkills = {
            'AWS Solutions Architect Professional': ['AWS', 'Cloud Infrastructure', 'System Architecture'],
            'Google Cloud Professional Data Engineer': ['Cloud Infrastructure', 'Data Science'],
            'Certified Kubernetes Administrator': ['Kubernetes', 'DevOps', 'Cloud Infrastructure']
          };
          
          const relevantSkills = certToSkills[cert.name] || [];
          relevantSkills.forEach(skillName => {
            const skillNodes = enhancedNodes.filter(node => 
              node.type === 'skill' && node.label === skillName
            );
            
            if (skillNodes.length > 0) {
              enhancedLinks.push({
                source: certId,
                target: skillNodes[0].id,
                value: 0.8,
                label: 'Validates'
              });
            }
          });
        });
      }
      
      // Add project nodes
      if (data.projects && Array.isArray(data.projects)) {
        data.projects.forEach((project, index) => {
          const projectId = `project-${project.name.replace(/\s+/g, '') || index}`;
          
          // Add project node
          enhancedNodes.push({
            id: projectId,
            label: project.name || `Project ${index + 1}`,
            type: 'company', // Reuse company type for styling
            size: 11,
            description: project.description || ''
          });
          
          // Link project to person
          enhancedLinks.push({
            source: personId,
            target: projectId,
            value: 1.2,
            label: 'Developed'
          });
          
          // Link project to relevant skills
          if (project.technologies && Array.isArray(project.technologies)) {
            project.technologies.forEach(tech => {
              const skillNodes = enhancedNodes.filter(node => 
                node.type === 'skill' && node.label === tech
              );
              
              if (skillNodes.length > 0) {
                enhancedLinks.push({
                  source: projectId,
                  target: skillNodes[0].id,
                  value: 0.9,
                  label: 'Used'
                });
              }
            });
          }
          
          // Link project to most recent company (likely where project was done)
          if (data.experiences && data.experiences.length > 0) {
            const latestCompany = data.experiences[0];
            const companyId = `company-${latestCompany.company.replace(/\s+/g, '') || 0}`;
            
            enhancedLinks.push({
              source: companyId,
              target: projectId,
              value: 1,
              label: 'Delivered at'
            });
          }
        });
      }
      
      // Set enhanced graph data
      setEnhancedGraphData({
        nodes: enhancedNodes,
        links: enhancedLinks
      });
      
    } catch (error) {
      console.error('Error transforming data to graph format:', error);
    }
  };

  // Generate a placeholder/demo data if none exists
  const generateDemoData = () => {
    const demoProfileData = {
      id: 'demo123',
      name: 'Alex Morgan',
      headline: 'Technology Leader with 15+ years experience across startups and enterprise',
      experiences: [
        {
          title: 'Chief Technology Officer',
          company: 'FutureTech AI',
          startDate: '2022-01',
          endDate: 'Present',
          description: 'Leading technology strategy and AI product development for a Series B startup focused on enterprise AI solutions'
        },
        {
          title: 'VP of Engineering',
          company: 'DataSphere',
          startDate: '2019-04',
          endDate: '2021-12',
          description: 'Scaled engineering team from 30 to 120, implemented agile methodologies, and rebuilt cloud infrastructure'
        },
        {
          title: 'Senior Engineering Manager',
          company: 'TechNova',
          startDate: '2017-06',
          endDate: '2019-03',
          description: 'Led multiple product engineering teams, launched three major products, and drove technology standardization'
        },
        {
          title: 'Software Engineering Lead',
          company: 'GlobalTech',
          startDate: '2014-08',
          endDate: '2017-05',
          description: 'Managed a team of 15 engineers, architected microservices infrastructure, and implemented CI/CD pipelines'
        },
        {
          title: 'Senior Software Engineer',
          company: 'InnovateLabs',
          startDate: '2012-03',
          endDate: '2014-07',
          description: 'Developed high-performance trading algorithms and real-time analytics platforms for financial services'
        },
        {
          title: 'Software Engineer',
          company: 'StartupXYZ',
          startDate: '2010-06',
          endDate: '2012-02',
          description: 'Built scalable backend systems and APIs for the company\'s mobile and web applications'
        },
        {
          title: 'Junior Developer',
          company: 'TechCorp',
          startDate: '2008-07',
          endDate: '2010-05',
          description: 'Developed features for enterprise content management system and improved performance by 40%'
        }
      ],
      skills: [
        { name: 'Engineering Leadership', endorsements: 42 },
        { name: 'System Architecture', endorsements: 38 },
        { name: 'Artificial Intelligence', endorsements: 27 },
        { name: 'Machine Learning', endorsements: 31 },
        { name: 'Cloud Infrastructure', endorsements: 35 },
        { name: 'DevOps', endorsements: 29 },
        { name: 'Agile Methodologies', endorsements: 33 },
        { name: 'Python', endorsements: 25 },
        { name: 'JavaScript', endorsements: 22 },
        { name: 'Java', endorsements: 20 },
        { name: 'Kubernetes', endorsements: 19 },
        { name: 'AWS', endorsements: 28 },
        { name: 'Product Development', endorsements: 26 },
        { name: 'Data Science', endorsements: 18 },
        { name: 'Microservices', endorsements: 23 },
        { name: 'Team Building', endorsements: 30 }
      ],
      education: [
        {
          school: 'Stanford University',
          degree: 'MBA',
          fieldOfStudy: 'Technology Management',
          startDate: '2015-09',
          endDate: '2017-06',
          description: 'Part-time executive MBA program focused on technology management and entrepreneurship'
        },
        {
          school: 'MIT',
          degree: 'MS',
          fieldOfStudy: 'Computer Science',
          startDate: '2006-09',
          endDate: '2008-05',
          description: 'Specialized in artificial intelligence and distributed systems'
        },
        {
          school: 'UC Berkeley',
          degree: 'BS',
          fieldOfStudy: 'Computer Science',
          startDate: '2002-09',
          endDate: '2006-05',
          description: 'Minor in Mathematics'
        }
      ],
      certifications: [
        {
          name: 'AWS Solutions Architect Professional',
          issuer: 'Amazon Web Services',
          date: '2020-05'
        },
        {
          name: 'Google Cloud Professional Data Engineer',
          issuer: 'Google',
          date: '2019-08'
        },
        {
          name: 'Certified Kubernetes Administrator',
          issuer: 'Cloud Native Computing Foundation',
          date: '2018-11'
        }
      ],
      projects: [
        {
          name: 'Enterprise AI Platform',
          description: 'Led development of an enterprise AI platform serving 200+ customers',
          technologies: ['Python', 'TensorFlow', 'AWS', 'Kubernetes']
        },
        {
          name: 'Real-time Analytics Engine',
          description: 'Built a scalable real-time analytics engine processing 500M events daily',
          technologies: ['Java', 'Apache Kafka', 'ElasticSearch', 'Redis']
        },
        {
          name: 'Cloud Migration Framework',
          description: 'Developed a framework to migrate legacy systems to cloud infrastructure',
          technologies: ['AWS', 'Terraform', 'Docker', 'Python']
        }
      ]
    };
    
    setProfileData(demoProfileData);
    transformDataToGraph(demoProfileData);
  };

  useEffect(() => {
    // If no data is available, generate demo data
    if (!profileData && !location.state?.profileData) {
      generateDemoData();
    }
  }, [profileData, location.state]);

  // Render detailed profile information
  const renderProfileDetails = () => {
    if (!profileData) {
      return (
        <Alert severity="info">No profile data available.</Alert>
      );
    }

    return (
      <Card sx={{ bgcolor: 'background.paper', color: 'text.primary' }}>
        <CardContent>
          <Typography variant="h4" gutterBottom>
            {profileData.name || 'Profile'}
          </Typography>
          
          <Typography variant="subtitle1" sx={{ mb: 2, color: 'primary.main' }}>
            {profileData.headline || ''}
          </Typography>
          
          <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
            Work Experience
          </Typography>
          <Divider sx={{ mb: 2 }} />
          
          {profileData.experiences && profileData.experiences.length > 0 ? (
            <List>
              {profileData.experiences.map((exp, index) => (
                <ListItem key={index} sx={{ display: 'block', mb: 2 }}>
                  <Typography variant="subtitle2" color="primary.main">
                    {exp.title || 'Role'}
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    {exp.company || 'Company'}
                    {exp.startDate && exp.endDate && 
                      ` (${exp.startDate.substring(0, 7)} - ${exp.endDate === 'Present' ? 'Present' : exp.endDate.substring(0, 7)})`
                    }
                  </Typography>
                  <Typography variant="body2">
                    {exp.description || ''}
                  </Typography>
                </ListItem>
              ))}
            </List>
          ) : (
            <Typography variant="body2">No work experience data available.</Typography>
          )}
          
          <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
            Skills
          </Typography>
          <Divider sx={{ mb: 2 }} />
          
          {profileData.skills && profileData.skills.length > 0 ? (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {profileData.skills.map((skill, index) => (
                <Chip
                  key={index}
                  label={`${skill.name} ${skill.endorsements ? `(${skill.endorsements})` : ''}`}
                  color="primary"
                  variant="outlined"
                  sx={{ m: 0.5 }}
                />
              ))}
            </Box>
          ) : (
            <Typography variant="body2">No skills data available.</Typography>
          )}
          
          <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
            Education
          </Typography>
          <Divider sx={{ mb: 2 }} />
          
          {profileData.education && profileData.education.length > 0 ? (
            <List>
              {profileData.education.map((edu, index) => (
                <ListItem key={index} sx={{ display: 'block', mb: 2 }}>
                  <Typography variant="subtitle2" color="primary.main">
                    {edu.school || 'Institution'}
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    {edu.degree || ''} {edu.fieldOfStudy || ''}
                    {edu.startDate && edu.endDate && 
                      ` (${edu.startDate.substring(0, 7)} - ${edu.endDate.substring(0, 7)})`
                    }
                  </Typography>
                  <Typography variant="body2">
                    {edu.description || ''}
                  </Typography>
                </ListItem>
              ))}
            </List>
          ) : (
            <Typography variant="body2">No education data available.</Typography>
          )}
          
          {/* Certifications Section */}
          {profileData.certifications && profileData.certifications.length > 0 && (
            <>
              <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
                Certifications
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              <List>
                {profileData.certifications.map((cert, index) => (
                  <ListItem key={index} sx={{ display: 'block', mb: 2 }}>
                    <Typography variant="subtitle2" color="primary.main">
                      {cert.name || `Certification ${index + 1}`}
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                      Issued by: {cert.issuer || 'Unknown'}
                      {cert.date && ` (${cert.date})`}
                    </Typography>
                  </ListItem>
                ))}
              </List>
            </>
          )}
          
          {/* Projects Section */}
          {profileData.projects && profileData.projects.length > 0 && (
            <>
              <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
                Key Projects
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              <List>
                {profileData.projects.map((project, index) => (
                  <ListItem key={index} sx={{ display: 'block', mb: 2 }}>
                    <Typography variant="subtitle2" color="primary.main">
                      {project.name || `Project ${index + 1}`}
                    </Typography>
                    <Typography variant="body2">
                      {project.description || ''}
                    </Typography>
                    {project.technologies && project.technologies.length > 0 && (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
                        {project.technologies.map((tech, techIndex) => (
                          <Chip 
                            key={techIndex} 
                            label={tech} 
                            size="small" 
                            variant="outlined" 
                            sx={{ 
                              bgcolor: 'rgba(9, 211, 172, 0.1)', 
                              borderColor: 'primary.main',
                              color: 'primary.main'
                            }} 
                          />
                        ))}
                      </Box>
                    )}
                  </ListItem>
                ))}
              </List>
            </>
          )}
        </CardContent>
      </Card>
    );
  };

  return (
    <Box
      sx={{
        width: '100%',
        minHeight: '90vh',
        py: 3,
        background: 'linear-gradient(135deg, #0F172A 0%, #25314D 100%)'
      }}
    >
      <Container maxWidth="xl">
        <Typography variant="h3" sx={{ color: 'white', fontWeight: 'bold', mb: 3 }}>
          Career Transition Insights
        </Typography>
        
        <Paper sx={{ mb: 3, bgcolor: 'background.paper', borderRadius: 2, overflow: 'hidden', boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)' }}>
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            textColor="primary"
            indicatorColor="primary"
            sx={{ borderBottom: 1, borderColor: 'divider' }}
          >
            <Tab label="Basic Network" />
            <Tab label="Enhanced Network" />
            <Tab label="Profile Details" />
          </Tabs>
          
          <Box sx={{ p: { xs: 1, sm: 2 } }}>
            {/* Basic Graph Visualization */}
            {activeTab === 0 && (
              <>
                <Typography variant="subtitle1" sx={{ mb: 2, mt: 1 }}>
                  Career Transition: Basic Network
                </Typography>
                {graphData.nodes.length > 0 ? (
                  <GraphVisualization data={graphData} />
                ) : (
                  <Alert severity="info" sx={{ mt: 2 }}>
                    No data available for visualization. Please upload a profile.
                  </Alert>
                )}
              </>
            )}
            
            {/* Enhanced Graph Visualization */}
            {activeTab === 1 && (
              <>
                <Typography variant="subtitle1" sx={{ mb: 2, mt: 1 }}>
                  Career Transition: Enhanced Network with Skills & Education
                </Typography>
                {enhancedGraphData.nodes.length > 0 ? (
                  <AdvancedGraphVisualization data={enhancedGraphData} />
                ) : (
                  <Alert severity="info" sx={{ mt: 2 }}>
                    No data available for visualization. Please upload a profile.
                  </Alert>
                )}
              </>
            )}
            
            {/* Profile Details */}
            {activeTab === 2 && (
              <>
                <Typography variant="subtitle1" sx={{ mb: 2, mt: 1 }}>
                  Profile Details
                </Typography>
                {renderProfileDetails()}
              </>
            )}
          </Box>
        </Paper>
      </Container>
    </Box>
  );
};

export default ResultsPage; 